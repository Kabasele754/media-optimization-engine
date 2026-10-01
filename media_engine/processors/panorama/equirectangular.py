from __future__ import annotations

import numpy as np
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from ...image_ops import normalized_image, encode_with_budget
from ...models import MediaAsset, PanoramaBuild
from ...locks import cache_lock, LeaseLost
from ...metrics import PANORAMA_STAGE_SECONDS, PANORAMA_BUILD_FAILURES
from ..base import ProcessorResult
from .tiles import TilePlan, generate_level
from .cube_tiles import CubeLevelPlan, generate_cube_level
from .publication import build_config, fingerprint, storage_prefix, publish, notify_publication


class PanoramaBusy(RuntimeError):
    """Another worker owns this asset/profile; retry instead of duplicating work."""


class Panorama360Processor:
    name = 'panorama_360'

    def supports(self, asset, profile_name):
        return getattr(asset, 'media_kind', '') == 'panorama' or profile_name.startswith('panorama.')

    def _lock(self, asset_id, profile, using):
        return cache_lock(f'moe:panorama:{asset_id}:{profile}',
            timeout=int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_LOCK_SECONDS', 900)),
            wait_timeout=0, using=using)

    def prepare(self, asset, profile_name, force=False):
        profile_name = profile_name if profile_name.startswith('panorama.') else 'panorama.multires'
        using = asset._state.db or 'default'
        with self._lock(asset.pk, profile_name, using) as lease:
            if not lease:
                raise PanoramaBusy('Panorama generation is already running')
            config = build_config(asset, profile_name)
            key = fingerprint(config)
            candidates = PanoramaBuild.objects.using(using).filter(asset=asset, profile=profile_name)
            if not force:
                ready = candidates.filter(fingerprint=key, state='READY', is_active=True).first()
                if ready:
                    return ready
            # Resume the latest interrupted build with the same frozen settings.
            build = candidates.filter(fingerprint=key).exclude(state='READY').order_by('-created_at').first()
            if build is None:
                build = PanoramaBuild.objects.using(using).create(asset=asset, profile=profile_name,
                    processor_version=config['processor_version'], fingerprint=key, config=config)
            if build.preview:
                return build
            try:
                with PANORAMA_STAGE_SECONDS.labels(stage='preview').time():
                    with default_storage.open(asset.original_file.name, 'rb') as source:
                        image = normalized_image(source).convert('RGB')
                    if image.size != (asset.width, asset.height):
                        raise ValueError('Panorama dimensions differ from the registered source')
                    width = max(1, min(image.width, config['preview_width']))
                    height = max(1, round(image.height * width / image.width))
                    preview = image.resize((width, height), Image.Resampling.LANCZOS)
                    encoded = encode_with_budget(preview, 'webp', config['preview_quality'],
                                                 target_bytes=config['preview_bytes'])
                    image.close()
                    preview.close()
                    lease.checkpoint(force=True)
                    stored = default_storage.save(storage_prefix(build) + 'preview.webp', ContentFile(encoded.content))
                    with lease.guard():
                        build.preview, build.state, build.last_error = stored, 'PREVIEW_READY', ''
                        build.save(update_fields=['preview', 'state', 'last_error', 'updated_at'])
                        has_active = candidates.filter(is_active=True).exists()
                        has_legacy = asset.panorama_tiles.filter(build__isnull=True, profile=profile_name, status='READY').exists()
                        if not has_active and not has_legacy:
                            MediaAsset.objects.using(using).filter(pk=asset.pk).update(
                                panorama_preview=stored, status=MediaAsset.Status.PARTIAL, last_error='', updated_at=timezone.now())
                        transaction.on_commit(lambda: notify_publication(str(asset.pk), profile_name,
                            str(build.pk), 'PREVIEW_READY'), using=using)
                return build
            except Exception as exc:
                self._record_failure(build, lease, exc)
                raise

    def _record_failure(self, build, lease, exc):
        PANORAMA_BUILD_FAILURES.inc()
        try:
            with lease.guard():
                build.state, build.last_error = 'FAILED', str(exc)[:2000]
                build.save(update_fields=['state', 'last_error', 'updated_at'])
                if not PanoramaBuild.objects.using(build._state.db or 'default').filter(asset=build.asset, is_active=True, state='READY').exists():
                    MediaAsset.objects.using(build._state.db or 'default').filter(pk=build.asset_id).update(last_error=build.last_error)
                transaction.on_commit(lambda: notify_publication(str(build.asset_id), build.profile,
                    str(build.pk), 'FAILED'), using=build._state.db or 'default')
        except LeaseLost:
            # A stale worker must not replace the new owner's state.
            pass

    def render(self, build_id, using='default'):
        build = PanoramaBuild.objects.using(using).select_related('asset').get(pk=build_id)
        with self._lock(build.asset_id, build.profile, using) as lease:
            if not lease:
                raise PanoramaBusy('Panorama generation is already running')
            build.refresh_from_db()
            asset = build.asset
            if build.state == 'READY':
                return ProcessorResult(str(asset.pk), self.name, 'READY')
            if not build.preview:
                raise ValueError('The preview must be prepared before tile generation')
            try:
                with PANORAMA_STAGE_SECONDS.labels(stage='tiles').time():
                    with default_storage.open(asset.original_file.name, 'rb') as source:
                        image = normalized_image(source).convert('RGB')
                    source_array = np.asarray(image) if build.config['layout'] == 'cube-multires' else None
                    completed = len(build.manifest.get('levels', []))
                    for plan in build.config['plans']:
                        lease.checkpoint(force=True)
                        if plan['level'] < completed:
                            continue
                        if build.config['layout'] == 'cube-multires':
                            fmt = build.config['formats'][0]
                            generate_cube_level(asset, image, profile=build.profile, version=build.processor_version,
                                plan=CubeLevelPlan(plan['level'], plan['size'], plan['tile_size']),
                                fmt=fmt, quality=build.config['quality'].get(fmt, 70),
                                build=build, lease=lease, source_array=source_array)
                        else:
                            for fmt in build.config['formats']:
                                generate_level(asset, image, profile=build.profile, version=build.processor_version,
                                    plan=TilePlan(plan['level'], plan['width'], plan['height'], plan['cols'], plan['rows'], plan['tile_size']),
                                    fmt=fmt, quality=build.config['quality'].get(fmt, 70), build=build, lease=lease)
                        publish(build, lease)
                    if build.config.get('cubemap'):
                        self._optional_cubemap(build, image, lease)
                    image.close()
                    publish(build, lease, final=True)
                asset.refresh_from_db()
                return ProcessorResult(str(asset.pk), self.name, asset.status)
            except Exception as exc:
                self._record_failure(build, lease, exc)
                raise

    def _optional_cubemap(self, build, image, lease):
        from .cubemap import iter_cubemap_faces
        if build.manifest.get('cubemap'):
            return
        size = min(build.config['cubemap_face_size'], max(16, image.height // 2))
        files = {}
        for name, face in iter_cubemap_faces(image, size, checkpoint=lease.checkpoint):
            encoded = encode_with_budget(face, 'webp', 76, target_bytes=None)
            lease.checkpoint(force=True)
            files[name] = default_storage.save(storage_prefix(build) + f'cube/{name}.webp', ContentFile(encoded.content))
            face.close()
        build.manifest['cubemap'] = {'face_size': size, 'format': 'webp', 'faces': files}

    def process(self, asset, profile_name, force=False):
        build = self.prepare(asset, profile_name, force=force)
        return self.render(build.pk, using=asset._state.db or 'default')
