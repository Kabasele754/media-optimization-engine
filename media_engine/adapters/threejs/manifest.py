from __future__ import annotations


def to_threejs(manifest: dict) -> dict:
    return {
        'type': 'equirectangular-multires',
        'preview': manifest.get('preview', ''),
        'levels': manifest.get('levels', []),
        'projection': manifest.get('projection', 'equirectangular'),
    }
