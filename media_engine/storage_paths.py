from pathlib import Path


def safe_extension(fmt):
    return {'JPEG': 'jpg', 'JPG': 'jpg', 'MPO': 'jpg', 'PNG': 'png', 'WEBP': 'webp', 'AVIF': 'avif'}.get(fmt.upper(), fmt.lower())


def original_storage_name(sha256_hex, extension):
    return f'media_engine/originals/{sha256_hex[:2]}/{sha256_hex[2:4]}/{sha256_hex}.{extension}'


def derivative_storage_name(sha256_hex, version, profile, width, fmt):
    return f'media_engine/derivatives/{sha256_hex[:2]}/{sha256_hex[2:4]}/v{version}/{profile}/{width}.{fmt}'
