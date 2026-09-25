import base64
import io
from dataclasses import dataclass
from PIL import Image, ImageOps
import numpy as np
from blurhash import encode as blurhash_encode
try:
    import pillow_avif  # noqa: F401
except Exception:
    pillow_avif = None


@dataclass
class EncodedImage:
    content: bytes
    width: int
    height: int
    quality: int


def normalized_image(source):
    image = Image.open(source)
    image.load()
    image = ImageOps.exif_transpose(image)
    if image.mode not in ('RGB', 'RGBA'):
        image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
    return image


def dominant_color(image):
    thumb = image.convert('RGB').resize((1, 1), Image.Resampling.LANCZOS)
    r, g, b = thumb.getpixel((0, 0))
    return f'#{r:02x}{g:02x}{b:02x}'


def make_blurhash(image):
    small = image.convert('RGB').resize((32, 32), Image.Resampling.LANCZOS)
    pixels = np.asarray(small)
    return blurhash_encode(pixels, components_x=4, components_y=3)


def placeholder_data_url(image):
    small = image.convert('RGB')
    small.thumbnail((32, 32), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    small.save(out, format='WEBP', quality=25, method=4)
    payload = base64.b64encode(out.getvalue()).decode('ascii')
    return f'data:image/webp;base64,{payload}'


def crop_to_ratio(image, ratio, focal_x=None, focal_y=None):
    target_ratio = ratio[0] / ratio[1]
    current_ratio = image.width / image.height
    if abs(target_ratio - current_ratio) < 0.001:
        return image

    fx = 0.5 if focal_x is None else min(1.0, max(0.0, focal_x))
    fy = 0.5 if focal_y is None else min(1.0, max(0.0, focal_y))

    if current_ratio > target_ratio:
        new_width = int(image.height * target_ratio)
        max_left = image.width - new_width
        left = int(max_left * fx)
        left = min(max(0, left), max_left)
        box = (left, 0, left + new_width, image.height)
    else:
        new_height = int(image.width / target_ratio)
        max_top = image.height - new_height
        top = int(max_top * fy)
        top = min(max(0, top), max_top)
        box = (0, top, image.width, top + new_height)
    return image.crop(box)


def resized(image, width, fit='contain', aspect_ratio=None, focal_x=None, focal_y=None):
    working = image
    if fit == 'cover' and aspect_ratio:
        working = crop_to_ratio(working, aspect_ratio, focal_x=focal_x, focal_y=focal_y)
    width = min(width, working.width)
    if width == working.width:
        return working.copy()
    height = round(working.height * width / working.width)
    return working.resize((width, height), Image.Resampling.LANCZOS)


def _save_kwargs(fmt, quality):
    fmt = fmt.lower()
    if fmt == 'avif':
        return {'format': 'AVIF', 'quality': quality, 'speed': 6}
    if fmt == 'webp':
        return {'format': 'WEBP', 'quality': quality, 'method': 6}
    if fmt in ('jpg', 'jpeg'):
        return {'format': 'JPEG', 'quality': quality, 'optimize': True, 'progressive': True}
    if fmt == 'png':
        return {'format': 'PNG', 'optimize': True}
    raise ValueError(f'Unsupported output format: {fmt}')


def _prepare_for_format(image, fmt):
    if fmt.lower() in ('jpeg', 'jpg') and image.mode == 'RGBA':
        canvas = Image.new('RGB', image.size, 'white')
        canvas.paste(image, mask=image.getchannel('A'))
        return canvas
    if fmt.lower() in ('jpeg', 'jpg') and image.mode != 'RGB':
        return image.convert('RGB')
    return image


def encode_with_budget(image, fmt, initial_quality, target_bytes=None, min_quality=35):
    image = _prepare_for_format(image, fmt)

    def encode(q):
        out = io.BytesIO()
        image.save(out, **_save_kwargs(fmt, q))
        return out.getvalue()

    quality = int(initial_quality)
    content = encode(quality)
    if not target_bytes or len(content) <= target_bytes or fmt.lower() == 'png':
        return EncodedImage(content, image.width, image.height, quality)

    low, high = min_quality, quality
    best = None
    best_q = min_quality
    smallest = content
    smallest_q = quality
    while low <= high:
        mid = (low + high) // 2
        candidate = encode(mid)
        if len(candidate) < len(smallest):
            smallest = candidate
            smallest_q = mid
        if len(candidate) <= target_bytes:
            best = candidate
            best_q = mid
            low = mid + 1
        else:
            high = mid - 1
    if best is None:
        best = smallest
        best_q = smallest_q
    return EncodedImage(best, image.width, image.height, best_q)
