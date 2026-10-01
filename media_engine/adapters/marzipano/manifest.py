from __future__ import annotations


def to_marzipano(manifest: dict) -> dict:
    """Support both explicit storage-safe tiles and compact immutable templates."""
    metadata = {key: manifest[key] for key in ('schema_version', 'revision', 'state', 'ready', 'complete',
        'processor_version', 'published_levels', 'expected_levels', 'updated_at', 'preview_projection') if key in manifest}
    if manifest.get('layout') != 'cube-multires':
        return {**metadata, 'type': 'equirectangular', 'preview': manifest.get('preview', ''),
            'projection': manifest.get('projection', 'equirectangular'), 'levels': manifest.get('levels', [])}
    levels, tiles = [], []
    preferred_format = manifest.get('format', 'webp')
    template = manifest.get('url_template', '')
    for item in manifest.get('levels', []):
        formats = item.get('formats', {})
        selected = formats.get('webp') or formats.get('avif') or next(iter(formats.values()), [])
        if not selected and not template:
            continue
        if not formats.get('webp') and formats.get('avif'):
            preferred_format = 'avif'
        levels.append({'level': item['level'], 'size': item.get('size') or item.get('width'),
            'tileSize': item.get('tile_size', 512),
            'fallbackOnly': bool(item.get('fallback_only', False)) and len(manifest.get('levels', [])) > 1})
        for tile in selected:
            tiles.append({'z': item['level'], 'face': tile.get('face', ''), 'x': tile['x'], 'y': tile['y'], 'url': tile['url']})
    result = {**metadata, 'type': 'cube-multires', 'preview': manifest.get('preview', ''),
        'projection': manifest.get('projection', 'equirectangular'), 'format': preferred_format,
        'geometry': {'type': 'cube', 'levels': levels}}
    if template:
        result['urlTemplate'] = template
    else:
        result['tiles'] = tiles
    return result
