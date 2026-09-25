from __future__ import annotations


def to_pannellum(manifest: dict) -> dict:
    levels = manifest.get('levels', [])
    if not levels:
        return {'type': 'equirectangular', 'panorama': manifest.get('preview', '')}
    max_level = max(level['level'] for level in levels)
    tile_size = levels[0].get('tile_size', 512)
    base = {
        'type': 'multires',
        'multiRes': {
            'basePath': '',
            'path': '{z}/{x}_{y}.webp',
            'fallbackPath': '{z}/{x}_{y}.webp',
            'extension': 'webp',
            'tileResolution': tile_size,
            'maxLevel': max_level,
            'cubeResolution': levels[-1].get('width', 0),
        },
        'preview': manifest.get('preview', ''),
    }
    return base
