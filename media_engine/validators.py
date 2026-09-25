import io
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image
try:
    import pillow_avif  # noqa: F401
except Exception:
    pillow_avif = None

ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP', 'AVIF'}
MIME_BY_FORMAT = {
    'JPEG': 'image/jpeg',
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
        width, height = image.size
        max_pixels = getattr(settings, 'MEDIA_ENGINE_MAX_PIXELS', 50_000_000)
        if width * height > max_pixels:
            raise ValidationError(f'Image exceeds maximum pixel count of {max_pixels}.')
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError('Invalid or corrupted image.') from exc
    return raw, fmt, MIME_BY_FORMAT[fmt], width, height
