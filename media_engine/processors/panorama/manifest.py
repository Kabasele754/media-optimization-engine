from __future__ import annotations

from copy import deepcopy
import hashlib
from urllib.parse import urlsplit

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db import connections

from ...models import PanoramaBuild
from .publication import complete_level, CUBE_FACES


def _url(name):
    if not name:
        return ''
    value = default_storage.url(name)
    cdn = str(getattr(settings, 'MEDIA_ENGINE_CDN_BASE_URL', '')).rstrip('/')
    return f'{cdn}{value}' if cdn and value.startswith('/') else value


def cache_namespace(using='default'):
    connection = connections[using]
    # Schema is optional; no dependency on a tenant framework.
    scope = ':'.join(str(part) for part in (getattr(settings, 'MEDIA_ENGINE_CACHE_NAMESPACE', ''),
        using, connection.settings_dict.get('NAME', ''), getattr(connection, 'schema_name', '')))
    return hashlib.sha256(scope.encode()).hexdigest()[:24]


def _legacy_snapshot(asset, profile):
    # Old rows remain readable, but never mix pipeline versions or new builds.
    rows = list(asset.panorama_tiles.filter(profile=profile, status='READY', build__isnull=True,
        processor_version=asset.processor_version).order_by('level', 'face', 'row', 'col').values(
        'level', 'face', 'col', 'row', 'format', 'file', 'file_size', 'width', 'height', 'level_width', 'level_height'))
    groups = {}
    for tile in rows:
        groups.setdefault(tile['level'], []).append(tile)
    cube = any(row['face'] for row in rows)
    levels = []
    for level_id in sorted(groups):
        if level_id != len(levels):
            break
        tiles = groups[level_id]
        edge = max(max(row['width'], row['height']) for row in tiles)
        width = max(row['level_width'] for row in tiles)
        height = max(row['level_height'] for row in tiles)
        if not width or not height:
            break
        plan = {'level': level_id, 'width': width, 'height': height, 'size': width if cube else 0,
                'tile_size': edge, 'cols': (width+edge-1)//edge, 'rows': (height+edge-1)//edge,
                'faces': list(CUBE_FACES) if cube else ['']}
        formats = sorted({row['format'] for row in tiles})
        if not complete_level(tiles, plan, formats):
            break
        grouped = {}
        for tile in tiles:
            grouped.setdefault(tile['format'], []).append({'face': tile['face'], 'x': tile['col'], 'y': tile['row'],
                'width': tile['width'], 'height': tile['height'], 'file': tile['file'], 'bytes': tile['file_size']})
        levels.append({**plan, 'formats': grouped, 'fallback_only': level_id == 0})
    pipeline = (asset.metadata_json or {}).get('panorama_pipeline', {})
    expected = pipeline.get('levels', 0)
    return {'layout': 'cube-multires' if cube else 'equirectangular-grid', 'levels': levels,
            'expected_levels': expected, 'canonical_paths': False,
            'complete': bool(expected and len(levels) == expected and asset.status == 'READY')}


def _snapshot_for(asset, profile):
    using = asset._state.db or 'default'
    builds = PanoramaBuild.objects.using(using).filter(asset_id=asset.pk, profile=profile)
    active = builds.filter(is_active=True).values('id', 'state', 'preview', 'processor_version', 'updated_at').first()
    if active:
        # This key changes at every publication. A reader racing with publication
        # can only cache data under the old key, never poison the current key.
        key = f"moe:pano:snapshot:{cache_namespace(using)}:{active['id']}:{active['updated_at'].isoformat()}"
        description = cache.get(key)
        if description is None:
            description = builds.values_list('manifest', flat=True).get(pk=active['id'])
            cache.set(key, description, int(getattr(settings, 'MEDIA_ENGINE_MANIFEST_CACHE_SECONDS', 3600)))
        return deepcopy(description), active
    legacy = _legacy_snapshot(asset, profile)
    if legacy['levels']:
        return legacy, {'id': f'legacy-v{asset.processor_version}', 'state': 'READY' if legacy['complete'] else 'BASE_LEVEL_READY',
            'preview': asset.panorama_preview.name, 'processor_version': asset.processor_version, 'updated_at': asset.updated_at}
    pending = builds.exclude(preview='').order_by('-created_at').values('id', 'state', 'preview', 'processor_version', 'updated_at').first()
    return legacy, pending or {'id': '', 'state': 'PROCESSING', 'preview': asset.panorama_preview.name,
                               'processor_version': asset.processor_version, 'updated_at': asset.updated_at}


def panorama_manifest(asset, profile='panorama.multires', *, compact=False):
    description, publication = _snapshot_for(asset, profile)
    levels = deepcopy(description.get('levels', []))
    template = ''
    if compact and description.get('canonical_paths') and description.get('layout') == 'cube-multires':
        marker = '__moe_tile_template__'
        candidate = _url(description['prefix'] + marker)
        parts = urlsplit(candidate)
        if not parts.query and not parts.fragment and candidate.endswith(marker):
            template = candidate[:-len(marker)] + 'l{z}/{f}/{x}_{y}.' + description.get('format', 'webp')
    for level in levels:
        if template:
            level.pop('formats', None)
        else:
            for tiles in level.get('formats', {}).values():
                for tile in tiles:
                    tile['url'] = _url(tile.pop('file'))
    cubemap = deepcopy(description.get('cubemap'))
    if cubemap:
        cubemap['faces'] = {name: _url(path) for name, path in cubemap['faces'].items()}
    complete = publication['state'] == 'READY' and bool(levels)
    result = {'schema_version': 2, 'asset_id': str(asset.pk), 'media_kind': 'panorama',
        'projection': asset.projection or 'equirectangular',
        'layout': description.get('layout', 'equirectangular-grid'),
        'width': asset.width, 'height': asset.height, 'profile': profile,
        'levels': levels, 'preview': _url(publication['preview']), 'preview_projection': 'equirectangular',
        'dominant_color': asset.dominant_color, 'blurhash': asset.blurhash,
        'processor_version': publication['processor_version'], 'revision': str(publication['id']),
        'state': publication['state'], 'ready': bool(levels), 'complete': complete,
        'published_levels': len(levels), 'expected_levels': description.get('expected_levels', 0),
        'updated_at': publication['updated_at'].isoformat(), 'cubemap': cubemap}
    if template:
        result.update(url_template=template, format=description.get('format', 'webp'))
    return result
