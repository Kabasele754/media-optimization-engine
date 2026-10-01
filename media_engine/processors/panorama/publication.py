"""Versioned panorama publication. Snapshots contain storage names, not URLs."""
from __future__ import annotations

import hashlib
import json
import math
import re

from django.conf import settings
from django.db import transaction
from django.dispatch import Signal
from django.utils import timezone

from ...models import MediaAsset, PanoramaBuild
from .tiles import pyramid_widths
from .cube_tiles import cube_level_sizes

panorama_published = Signal()
CUBE_FACES = ('f', 'b', 'l', 'r', 'u', 'd')


def build_config(asset, profile):
    if not re.fullmatch(r'panorama\.[a-zA-Z0-9_.-]+', profile):
        raise ValueError('Invalid panorama profile')
    tile_size = int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_TILE_SIZE', 512))
    if tile_size < 16 or tile_size > 2048 or tile_size & (tile_size - 1):
        raise ValueError('Panorama tile size must be a power of two between 16 and 2048')
    cube = profile in {'panorama.marzipano', 'panorama.cube'}
    if cube:
        widths = cube_level_sizes(asset.width,
            min_size=int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBE_MIN_SIZE', 256)),
            max_size=int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBE_MAX_SIZE', 4096)))
        formats = [str(getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBE_FORMAT', 'webp')).lower()]
        quality = {formats[0]: int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBE_QUALITY', 72))}
    else:
        widths = pyramid_widths(asset.width,
            min_width=int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_MIN_LEVEL_WIDTH', 1024)))
        formats = list(dict.fromkeys(getattr(settings, 'MEDIA_ENGINE_PANORAMA_FORMATS', ('avif', 'webp'))))
        quality = dict(getattr(settings, 'MEDIA_ENGINE_PANORAMA_QUALITY', {'avif': 52, 'webp': 72}))
    if not formats or any(fmt not in {'webp', 'avif', 'jpeg'} for fmt in formats):
        raise ValueError('Unsupported panorama format')
    if any(not 1 <= int(quality.get(fmt, 70)) <= 100 for fmt in formats):
        raise ValueError('Panorama quality must be between 1 and 100')
    plans = []
    for level, width in enumerate(widths):
        height = width if cube else max(1, width // 2)
        edge = min(tile_size, width, height)
        plans.append({'level': level, 'width': width, 'height': height,
                      'size': width if cube else 0, 'tile_size': edge,
                      'cols': math.ceil(width / edge), 'rows': math.ceil(height / edge),
                      'faces': list(CUBE_FACES) if cube else ['']})
    return {'schema': 2, 'algorithm': 'bilinear-banded-v1',
            'source_sha256': asset.original_sha256,
            'width': asset.width, 'height': asset.height,
            'processor_version': int(getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)),
            'profile': profile, 'layout': 'cube-multires' if cube else 'equirectangular-grid',
            'formats': formats, 'quality': quality, 'plans': plans,
            'preview_width': min(asset.width, int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_PREVIEW_WIDTH', 1024))),
            'preview_quality': int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_PREVIEW_QUALITY', 58)),
            'preview_bytes': int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_PREVIEW_BYTES', 140000)),
            'cubemap': bool(getattr(settings, 'MEDIA_ENGINE_PANORAMA_GENERATE_CUBEMAP', False)) and not cube,
            'cubemap_face_size': int(getattr(settings, 'MEDIA_ENGINE_PANORAMA_CUBEMAP_FACE_SIZE', 2048))}


def fingerprint(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def storage_prefix(build):
    sha = build.asset.original_sha256
    return f'media_engine/panoramas/{sha[:2]}/{sha}/v{build.processor_version}/{build.profile}/r{build.id.hex}/'


def complete_level(records, plan, formats):
    """Require every coordinate, correct dimensions, and non-empty storage keys."""
    expected = {(face, x, y, fmt) for face in plan['faces']
                for y in range(plan['rows']) for x in range(plan['cols']) for fmt in formats}
    actual = set()
    for tile in records:
        key = (tile['face'], tile['col'], tile['row'], tile['format'])
        if key not in expected or key in actual:
            return False
        x, y = tile['col'], tile['row']
        width = min(plan['tile_size'], plan['width'] - x * plan['tile_size'])
        height = min(plan['tile_size'], plan['height'] - y * plan['tile_size'])
        if (tile['width'], tile['height']) != (width, height):
            return False
        if not tile['file'] or tile.get('file_size', 0) <= 0:
            return False
        if (tile.get('level_width', plan['width']), tile.get('level_height', plan['height'])) != (plan['width'], plan['height']):
            return False
        actual.add(key)
    return actual == expected


def snapshot(build):
    config = build.config
    rows = list(build.tiles.filter(status='READY').values(
        'level', 'face', 'col', 'row', 'format', 'file', 'file_size', 'width', 'height', 'level_width', 'level_height'))
    groups = {}
    for row in rows:
        groups.setdefault(row['level'], []).append(row)
    levels = []
    canonical_paths = True
    prefix = storage_prefix(build)
    for plan in config['plans']:
        records = groups.get(plan['level'], [])
        if not complete_level(records, plan, config['formats']):
            break  # Never expose holes in the pyramid.
        formats = {}
        for tile in sorted(records, key=lambda t: (t['format'], t['face'], t['row'], t['col'])):
            face_path = f"{tile['face']}/" if tile['face'] else ''
            expected_path = f"{prefix}l{plan['level']}/{face_path}{tile['col']}_{tile['row']}.{tile['format']}"
            canonical_paths = canonical_paths and tile['file'] == expected_path
            formats.setdefault(tile['format'], []).append({
                'face': tile['face'], 'x': tile['col'], 'y': tile['row'],
                'width': tile['width'], 'height': tile['height'],
                'file': tile['file'], 'bytes': tile['file_size']})
        levels.append({**plan, 'formats': formats, 'fallback_only': plan['level'] == 0})
    return {'levels': levels, 'canonical_paths': canonical_paths, 'prefix': prefix,
            'expected_levels': len(config['plans']), 'layout': config['layout'],
            'format': config['formats'][0], 'formats': config['formats'],
            'cubemap': build.manifest.get('cubemap')}


def notify_publication(asset_id, profile, revision, state):
    from ...manifest import invalidate_manifest
    invalidate_manifest(asset_id)
    # An optional host integration must not make the processing task fail.
    panorama_published.send_robust(sender=PanoramaBuild, asset_id=asset_id,
                                  profile=profile, revision=revision, state=state)


def publish(build, lease, *, final=False):
    description = snapshot(build)
    if final and len(description['levels']) != description['expected_levels']:
        raise ValueError('Cannot publish an incomplete panorama pyramid')
    if not description['levels']:
        return
    new_state = PanoramaBuild.State.READY if final else PanoramaBuild.State.BASE_LEVEL_READY
    using = build._state.db or 'default'
    with lease.guard():
        asset = MediaAsset.objects.using(using).select_for_update().get(pk=build.asset_id)
        active = PanoramaBuild.objects.using(using).filter(asset_id=asset.pk, profile=build.profile, is_active=True).first()
        # A complete previous generation stays online during a rebuild.
        legacy_serving = active is None and asset.status == MediaAsset.Status.READY and asset.panorama_tiles.filter(
            build__isnull=True, profile=build.profile, status='READY').exists()
        activate = final or (active is None and not legacy_serving) or (active is not None and active.pk == build.pk)
        build.manifest = description
        build.state = new_state
        build.last_error = ''
        if final:
            build.completed_at = timezone.now()
        if activate:
            PanoramaBuild.objects.using(using).filter(asset_id=asset.pk, profile=build.profile, is_active=True).exclude(pk=build.pk).update(is_active=False)
            build.is_active = True
        build.save()
        if activate:
            asset.panorama_preview = build.preview.name
            asset.status = MediaAsset.Status.READY if final else MediaAsset.Status.PARTIAL
            asset.processor_version = build.processor_version
            asset.processor = 'panorama_360'
            asset.media_kind = 'panorama'
            asset.projection = asset.projection or 'equirectangular'
            asset.last_error = ''
            asset.processed_at = timezone.now() if final else asset.processed_at
            metadata = dict(asset.metadata_json or {})
            metadata['panorama_pipeline'] = {'layout': description['layout'], 'levels': len(description['levels']),
                'formats': description['formats'], 'revision': str(build.pk)}
            asset.metadata_json = metadata
            asset.save(update_fields=['panorama_preview', 'status', 'processor_version', 'processor',
                'media_kind', 'projection', 'last_error', 'processed_at', 'metadata_json', 'updated_at'])
        transaction.on_commit(lambda: notify_publication(str(asset.pk), build.profile, str(build.pk), new_state), using=using)
