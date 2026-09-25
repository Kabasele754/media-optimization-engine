from __future__ import annotations


def to_marzipano(manifest: dict) -> dict:
    """Return a browser-friendly Marzipano description.

    For ``panorama.marzipano`` the engine emits a true multires CubeGeometry
    pyramid. Tiles stay explicit so this works with local storage, S3 and R2
    without assuming a specific URL layout.
    """
    layout = manifest.get('layout', '')
    if layout != 'cube-multires':
        # Graceful preview fallback for a generic equirectangular pipeline.
        return {
            'type': 'equirectangular',
            'preview': manifest.get('preview', ''),
            'projection': manifest.get('projection', 'equirectangular'),
            'levels': manifest.get('levels', []),
        }

    levels = []
    tiles = []
    preferred_format = 'webp'
    for item in manifest.get('levels', []):
        formats = item.get('formats', {})
        selected = formats.get('webp') or formats.get('avif') or next(iter(formats.values()), [])
        if not selected:
            continue
        if formats.get('webp') is None and formats.get('avif'):
            preferred_format = 'avif'
        levels.append({
            'level': item['level'],
            'size': item.get('size') or item.get('width'),
            'tileSize': item.get('tile_size', 512),
            'fallbackOnly': bool(item.get('fallback_only', False)),
        })
        for tile in selected:
            tiles.append({
                'z': item['level'],
                'face': tile.get('face', ''),
                'x': tile['x'],
                'y': tile['y'],
                'url': tile['url'],
            })

    return {
        'type': 'cube-multires',
        'preview': manifest.get('preview', ''),
        'projection': manifest.get('projection', 'equirectangular'),
        'format': preferred_format,
        'geometry': {'type': 'cube', 'levels': levels},
        'tiles': tiles,
    }
