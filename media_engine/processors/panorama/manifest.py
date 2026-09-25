from __future__ import annotations

from collections import defaultdict
from django.conf import settings


def panorama_manifest(asset, profile: str = 'panorama.multires') -> dict:
    qs = asset.panorama_tiles.filter(profile=profile, status='READY').order_by('level', 'face', 'row', 'col')
    is_cube = qs.exclude(face='').exists()

    if is_cube:
        groups = defaultdict(lambda: {
            'formats': defaultdict(list),
            'size': 0,
            'cols': 0,
            'rows': 0,
            'faces': set(),
        })
        for tile in qs:
            level = groups[tile.level]
            level['size'] = max(level['size'], tile.level_width, tile.level_height)
            level['cols'] = max(level['cols'], tile.col + 1)
            level['rows'] = max(level['rows'], tile.row + 1)
            level['faces'].add(tile.face)
            level['formats'][tile.format].append({
                'face': tile.face,
                'x': tile.col,
                'y': tile.row,
                'width': tile.width,
                'height': tile.height,
                'url': tile.file.url,
                'bytes': tile.file_size,
            })
        levels = []
        for level_id in sorted(groups):
            item = groups[level_id]
            levels.append({
                'level': level_id,
                'size': item['size'],
                'width': item['size'],
                'height': item['size'],
                'cols': item['cols'],
                'rows': item['rows'],
                'tile_size': getattr(settings, 'MEDIA_ENGINE_PANORAMA_TILE_SIZE', 512),
                'faces': sorted(item['faces']),
                'formats': dict(item['formats']),
            })
        return {
            'asset_id': str(asset.pk),
            'media_kind': 'panorama',
            'projection': asset.projection or 'equirectangular',
            'layout': 'cube-multires',
            'width': asset.width,
            'height': asset.height,
            'profile': profile,
            'levels': levels,
            'preview': asset.panorama_preview.url if asset.panorama_preview else '',
            'dominant_color': asset.dominant_color,
            'blurhash': asset.blurhash,
            'processor_version': asset.processor_version,
            'cubemap': (asset.metadata_json or {}).get('cubemap'),
        }

    groups = defaultdict(lambda: {'formats': defaultdict(list), 'width': 0, 'height': 0, 'cols': 0, 'rows': 0})
    for tile in qs:
        level = groups[tile.level]
        level['width'] = max(level['width'], tile.level_width)
        level['height'] = max(level['height'], tile.level_height)
        level['cols'] = max(level['cols'], tile.col + 1)
        level['rows'] = max(level['rows'], tile.row + 1)
        level['formats'][tile.format].append({
            'x': tile.col,
            'y': tile.row,
            'width': tile.width,
            'height': tile.height,
            'url': tile.file.url,
            'bytes': tile.file_size,
        })
    levels = []
    for level_id in sorted(groups):
        item = groups[level_id]
        levels.append({
            'level': level_id,
            'width': item['width'],
            'height': item['height'],
            'cols': item['cols'],
            'rows': item['rows'],
            'tile_size': getattr(settings, 'MEDIA_ENGINE_PANORAMA_TILE_SIZE', 512),
            'formats': dict(item['formats']),
        })
    return {
        'asset_id': str(asset.pk),
        'media_kind': 'panorama',
        'projection': asset.projection or 'equirectangular',
        'layout': 'equirectangular-grid',
        'width': asset.width,
        'height': asset.height,
        'profile': profile,
        'levels': levels,
        'preview': asset.panorama_preview.url if asset.panorama_preview else '',
        'dominant_color': asset.dominant_color,
        'blurhash': asset.blurhash,
        'processor_version': asset.processor_version,
        'cubemap': (asset.metadata_json or {}).get('cubemap'),
    }
