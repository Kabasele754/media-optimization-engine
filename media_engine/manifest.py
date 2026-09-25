from django.conf import settings
from django.core.cache import cache
from .models import MediaAsset, MediaVariant
from .profiles import get_profile


def manifest_cache_key(asset_id, profile='default'):
    version = getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)
    return f'media-engine:manifest:v{version}:{asset_id}:{profile}'


def invalidate_manifest(asset_id):
    profiles = set(getattr(settings, 'MEDIA_ENGINE_PROFILES', {}).keys())
    profiles.update({'panorama.multires', 'panorama.preview', 'panorama.marzipano', 'panorama.cube'})
    for profile in profiles:
        cache.delete(manifest_cache_key(asset_id, profile))


def public_url(file_field):
    url = file_field.url
    cdn = getattr(settings, 'MEDIA_ENGINE_CDN_BASE_URL', '')
    if cdn and url.startswith('/'):
        return f'{cdn}{url}'
    return url


def _standard_manifest(asset, profile):
    profile_cfg = get_profile(profile)
    version = getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)
    variants = MediaVariant.objects.filter(
        asset=asset,
        profile=profile,
        processor_version=version,
        status=MediaVariant.Status.READY,
    ).order_by('width')
    grouped = {}
    for variant in variants:
        grouped.setdefault(variant.format, []).append({
            'width': variant.width,
            'height': variant.height,
            'url': public_url(variant.file),
            'bytes': variant.file_size,
            'quality': variant.quality,
        })
    fallback_format = profile_cfg.get('fallback_format', 'jpeg')
    fallback = (grouped.get(fallback_format) or grouped.get('webp') or grouped.get('avif') or [])[-1:] or None
    return {
        'id': str(asset.id),
        'status': asset.status,
        'media_kind': asset.media_kind,
        'projection': asset.projection,
        'sha256': asset.original_sha256,
        'width': asset.width,
        'height': asset.height,
        'dominant_color': asset.dominant_color,
        'blurhash': asset.blurhash,
        'placeholder_data_url': asset.placeholder_data_url,
        'profile': profile,
        'processor': asset.processor,
        'processor_version': version,
        'variants': grouped,
        'fallback': fallback[0] if fallback else None,
        'original_url': public_url(asset.original_file) if getattr(settings, 'MEDIA_ENGINE_PUBLIC_ORIGINAL_FALLBACK', False) else None,
    }


def build_manifest(asset_or_id, profile='default'):
    asset_id = getattr(asset_or_id, 'id', asset_or_id)
    key = manifest_cache_key(asset_id, profile)
    cached = cache.get(key)
    if cached:
        return cached
    asset = asset_or_id if isinstance(asset_or_id, MediaAsset) else MediaAsset.objects.get(pk=asset_id)
    if asset.media_kind == 'panorama' or profile.startswith('panorama.'):
        from .processors.panorama.manifest import panorama_manifest
        result = panorama_manifest(asset, profile=profile if profile.startswith('panorama.') else 'panorama.multires')
        if result.get('preview'):
            result['preview'] = public_url(asset.panorama_preview)
        for level in result.get('levels', []):
            for tiles in level.get('formats', {}).values():
                for tile in tiles:
                    url = tile.get('url', '')
                    cdn = getattr(settings, 'MEDIA_ENGINE_CDN_BASE_URL', '')
                    if cdn and url.startswith('/'):
                        tile['url'] = f'{cdn}{url}'
    else:
        result = _standard_manifest(asset, profile)
    cache.set(key, result, 3600)
    return result
