from __future__ import annotations

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from ...image_ops import normalized_image, encode_with_budget
from ...models import MediaAsset, PanoramaTile
from ..base import ProcessorResult
from .tiles import pyramid_widths, build_plan, generate_level
from .cube_tiles import cube_level_sizes, CubeLevelPlan, generate_cube_level


class Panorama360Processor:
    name = 'panorama_360'

    def supports(self, asset, profile_name: str) -> bool:
        return getattr(asset, 'media_kind', '') == 'panorama' or profile_name.startswith('panorama.')

    def _write_preview(self, asset, image, *, version: int, profile_name: str):
        preview_width = min(1024, asset.width)
        preview_height = max(1, preview_width // 2)
        preview = image.resize((preview_width, preview_height))
        encoded_preview = encode_with_budget(preview, 'webp', 58, target_bytes=140000)
        preview_path = (
            f'media_engine/panoramas/{asset.original_sha256[:2]}/'
            f'{asset.original_sha256}/v{version}/{profile_name}/preview.webp'
        )
        if default_storage.exists(preview_path):
            default_storage.delete(preview_path)
        asset.panorama_preview = default_storage.save(preview_path, ContentFile(encoded_preview.content))

    def _process_equirect_tiles(self, asset, image, *, version: int, profile_name: str, force: bool):
        tile_size = getattr(settings, 'MEDIA_ENGINE_PANORAMA_TILE_SIZE', 512)
        min_width = getattr(settings, 'MEDIA_ENGINE_PANORAMA_MIN_LEVEL_WIDTH', 1024)
        formats = tuple(getattr(settings, 'MEDIA_ENGINE_PANORAMA_FORMATS', ('avif', 'webp')))
        quality_map = getattr(settings, 'MEDIA_ENGINE_PANORAMA_QUALITY', {'avif': 52, 'webp': 72})
        widths = pyramid_widths(asset.width, min_width=min_width)
        for level, width in enumerate(widths):
            plan = build_plan(width, tile_size, level)
            for fmt in formats:
                generate_level(
                    asset,
                    image,
                    profile=profile_name,
                    version=version,
                    plan=plan,
                    fmt=fmt,
                    quality=quality_map.get(fmt, 70),
                    force=force,
                )
                PanoramaTile.objects.filter(
                    asset=asset,
                    profile=profile_name,
                    processor_version=version,
                    level=level,
                    face='',
                ).update(level_width=plan.width, level_height=plan.height)
        return {'layout': 'equirectangular-grid', 'levels': len(widths), 'formats': list(formats)}

    def _process_marzipano_cube(self, asset, image, *, version: int, profile_name: str, force: bool):
        tile_size = getattr(settings, 'MEDIA_ENGINE_PANORAMA_TILE_SIZE', 512)
        min_size = getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBE_MIN_SIZE', 512)
        max_size = getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBE_MAX_SIZE', 4096)
        fmt = getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBE_FORMAT', 'webp').lower()
        quality = int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBE_QUALITY', 72))
        sizes = cube_level_sizes(asset.width, min_size=min_size, max_size=max_size)
        for level, size in enumerate(sizes):
            generate_cube_level(
                asset,
                image,
                profile=profile_name,
                version=version,
                plan=CubeLevelPlan(level=level, size=size, tile_size=tile_size),
                fmt=fmt,
                quality=quality,
                force=force,
            )
        return {
            'layout': 'cube-multires',
            'levels': len(sizes),
            'face_sizes': sizes,
            'format': fmt,
            'tile_size': tile_size,
        }

    def process(self, asset, profile_name: str, force: bool = False) -> ProcessorResult:
        version = getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)
        asset.status = MediaAsset.Status.PROCESSING
        asset.last_error = ''
        asset.save(update_fields=['status', 'last_error', 'updated_at'])
        try:
            with default_storage.open(asset.original_file.name, 'rb') as source:
                image = normalized_image(source).convert('RGB')
            self._write_preview(asset, image, version=version, profile_name=profile_name)

            PanoramaTile.objects.filter(
                asset=asset,
                profile=profile_name,
                processor_version=version,
            ).exclude(status=PanoramaTile.Status.READY).delete()

            if profile_name in {'panorama.marzipano', 'panorama.cube'}:
                pipeline = self._process_marzipano_cube(
                    asset, image, version=version, profile_name=profile_name, force=force
                )
            else:
                pipeline = self._process_equirect_tiles(
                    asset, image, version=version, profile_name=profile_name, force=force
                )

            metadata = dict(asset.metadata_json or {})
            metadata['panorama_pipeline'] = pipeline
            if getattr(settings, 'MEDIA_ENGINE_PANORAMA_GENERATE_CUBEMAP', False) and profile_name not in {'panorama.marzipano', 'panorama.cube'}:
                from .cubemap import equirectangular_to_cubemap
                face_size = min(
                    getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBEMAP_FACE_SIZE', 2048),
                    max(256, asset.height // 2),
                )
                faces = equirectangular_to_cubemap(image, face_size)
                face_urls = {}
                for face_name, face_image in faces.items():
                    encoded_face = encode_with_budget(face_image, 'webp', 76, target_bytes=None)
                    face_path = (
                        f'media_engine/panoramas/{asset.original_sha256[:2]}/'
                        f'{asset.original_sha256}/v{version}/{profile_name}/cube/{face_name}.webp'
                    )
                    if default_storage.exists(face_path):
                        default_storage.delete(face_path)
                    stored_face = default_storage.save(face_path, ContentFile(encoded_face.content))
                    face_urls[face_name] = default_storage.url(stored_face)
                metadata['cubemap'] = {'face_size': face_size, 'format': 'webp', 'faces': face_urls}

            asset.metadata_json = metadata
            asset.media_kind = 'panorama'
            asset.projection = asset.projection or 'equirectangular'
            asset.processor = self.name
            asset.processor_version = version
            asset.status = MediaAsset.Status.READY
            asset.processed_at = timezone.now()
            asset.last_error = ''
            asset.save()
        except Exception as exc:
            asset.status = MediaAsset.Status.FAILED
            asset.last_error = str(exc)
            asset.save(update_fields=['status', 'last_error', 'updated_at'])
            raise
        return ProcessorResult(str(asset.pk), self.name, asset.status)
