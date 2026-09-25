from django.conf import settings

DEFAULT_PROFILES = {
    'default': {
        'widths': [320, 480, 640, 960, 1280, 1600],
        'formats': ['avif', 'webp'],
        'fallback_format': 'jpeg',
        'fit': 'contain',
        'quality': {'avif': 52, 'webp': 72, 'jpeg': 80},
        'target_bytes': {},
    },
    'avatar': {
        'widths': [96, 192, 384],
        'formats': ['avif', 'webp'],
        'fallback_format': 'jpeg',
        'fit': 'cover',
        'aspect_ratio': [1, 1],
        'quality': {'avif': 48, 'webp': 68, 'jpeg': 78},
        'target_bytes': {96: 25000, 192: 40000, 384: 70000},
    },
    'card': {
        'widths': [320, 480, 640, 768],
        'formats': ['avif', 'webp'],
        'fallback_format': 'jpeg',
        'fit': 'cover',
        'aspect_ratio': [4, 3],
        'quality': {'avif': 50, 'webp': 70, 'jpeg': 80},
        'target_bytes': {320: 45000, 480: 70000, 640: 95000, 768: 120000},
    },
    'hero': {
        'widths': [640, 960, 1280, 1600, 1920],
        'formats': ['avif', 'webp'],
        'fallback_format': 'jpeg',
        'fit': 'cover',
        'aspect_ratio': [16, 9],
        'quality': {'avif': 56, 'webp': 76, 'jpeg': 84},
        'target_bytes': {640: 120000, 960: 170000, 1280: 220000, 1600: 300000, 1920: 360000},
    },
    'panorama.preview': {
        'widths': [1024],
        'formats': ['webp'],
        'fallback_format': 'jpeg',
        'fit': 'contain',
        'quality': {'webp': 58, 'jpeg': 72},
        'target_bytes': {1024: 140000},
    },
    'panorama.multires': {
        'widths': [],
        'formats': ['avif', 'webp'],
        'fallback_format': 'webp',
        'fit': 'contain',
        'quality': {'avif': 52, 'webp': 72},
        'target_bytes': {},
        'tile_size': 512,
        'projection': 'equirectangular',
    },
}


def get_profile(name):
    profiles = DEFAULT_PROFILES.copy()
    profiles.update(getattr(settings, 'MEDIA_ENGINE_PROFILES', {}) or {})
    if name not in profiles:
        raise KeyError(f'Unknown media profile: {name}')
    return profiles[name]


def requested_widths(profile, original_width):
    return [w for w in profile.get('widths', []) if w <= original_width] or [min(original_width, max(profile.get('widths', [original_width])))]


def all_formats(profile):
    formats = list(profile.get('formats', []))
    fallback = profile.get('fallback_format')
    if fallback and fallback not in formats:
        formats.append(fallback)
    return formats
