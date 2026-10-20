import io
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image
from .audio_ops import AUDIO_EXTENSIONS, AUDIO_MIME_BY_EXTENSION, probe_audio_bytes
try:
    import pillow_avif  # noqa: F401
except Exception:
    pillow_avif = None

ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP', 'AVIF', 'MPO'}
MIME_BY_FORMAT = {
    'JPEG': 'image/jpeg',
    'MPO': 'image/jpeg',
    'PNG': 'image/png',
    'WEBP': 'image/webp',
    'AVIF': 'image/avif',
}


def inspect_upload(uploaded_file):
    max_bytes = getattr(settings, 'MEDIA_ENGINE_MAX_UPLOAD_BYTES', 25 * 1024 * 1024)
    if uploaded_file.size > max_bytes:
        raise ValidationError(f'Image exceeds maximum upload size of {max_bytes} bytes.')

    uploaded_file.seek(0)
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw))
        fmt = (image.format or '').upper()
        if fmt not in ALLOWED_FORMATS:
            raise ValidationError(f'Unsupported image format: {fmt or "unknown"}')
        # Pillow reports some JPEG containers as MPO. For optimization purposes,
        # the primary frame is a normal JPEG-compatible raster and can safely
        # enter the standard image pipeline.
        if fmt == 'MPO':
            fmt = 'JPEG'
        width, height = image.size
        max_pixels = getattr(settings, 'MEDIA_ENGINE_MAX_PIXELS', 50_000_000)
        if width * height > max_pixels:
            raise ValidationError(f'Image exceeds maximum pixel count of {max_pixels}.')
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError('Invalid or corrupted image.') from exc
    return raw, fmt, MIME_BY_FORMAT[fmt], width, height


def inspect_audio_upload(uploaded_file, *, profile=None):
    profile = profile or {}
    max_bytes = getattr(settings, 'MEDIA_ENGINE_MAX_AUDIO_UPLOAD_BYTES', 20 * 1024 * 1024)
    if uploaded_file.size > max_bytes:
        raise ValidationError(f'Audio exceeds maximum upload size of {max_bytes} bytes.')

    extension = Path(getattr(uploaded_file, 'name', '') or '').suffix.lower().lstrip('.')
    if extension not in AUDIO_EXTENSIONS:
        raise ValidationError('Unsupported audio format.')

    uploaded_file.seek(0)
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    metadata = probe_audio_bytes(raw, suffix='.' + extension)

    max_duration = int(profile.get('max_duration_seconds') or 600)
    if metadata['duration_ms'] > max_duration * 1000:
        raise ValidationError(f'Audio exceeds maximum duration of {max_duration} seconds.')

    return raw, extension.upper(), AUDIO_MIME_BY_EXTENSION[extension], metadata
