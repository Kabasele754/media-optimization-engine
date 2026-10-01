from __future__ import annotations

import math
import numpy as np
from PIL import Image

_FACE_VECTORS = {
    'front': lambda a, b: (a, b, np.ones_like(a)),
    'back': lambda a, b: (-a, b, -np.ones_like(a)),
    'left': lambda a, b: (-np.ones_like(a), b, a),
    'right': lambda a, b: (np.ones_like(a), b, -a),
    'top': lambda a, b: (a, np.ones_like(a), -b),
    'bottom': lambda a, b: (a, -np.ones_like(a), b),
}


def _sample_equirectangular(array, x, y, z):
    """Bilinear sampling at pixel centers, with longitude wrapping."""
    norm = np.sqrt(x * x + y * y + z * z)
    lon = np.arctan2(x, z)
    lat = np.arcsin(np.clip(y / norm, -1, 1))
    h, w = array.shape[:2]
    px = (lon / (2 * math.pi) + 0.5) * w - 0.5
    py = np.clip((0.5 - lat / math.pi) * h - 0.5, 0, h - 1)
    x0 = np.floor(px).astype(np.int32)
    y0 = np.floor(py).astype(np.int32)
    fx, fy = (px - x0)[..., None], (py - y0)[..., None]
    x1, y1 = (x0 + 1) % w, np.minimum(y0 + 1, h - 1)
    x0 %= w
    top = array[y0, x0] * (1 - fx) + array[y0, x1] * fx
    bottom = array[y1, x0] * (1 - fx) + array[y1, x1] * fx
    return np.clip(np.rint(top * (1 - fy) + bottom * fy), 0, 255).astype(np.uint8)


def iter_cubemap_faces(image, face_size, *, faces=None, rows_per_chunk=128, checkpoint=None, source_array=None):
    """Only one face and a bounded coordinate band are allocated at a time."""
    if face_size < 1 or rows_per_chunk < 1:
        raise ValueError('Face size and chunk size must be positive')
    src = source_array if source_array is not None else np.asarray(image.convert('RGB'))
    axis = ((np.arange(face_size, dtype=np.float32) + 0.5) / face_size) * 2 - 1
    for name in faces or _FACE_VECTORS:
        output = np.empty((face_size, face_size, 3), dtype=np.uint8)
        for start in range(0, face_size, rows_per_chunk):
            if checkpoint:
                checkpoint()
            end = min(face_size, start + rows_per_chunk)
            a, b = np.meshgrid(axis, -axis[start:end])
            output[start:end] = _sample_equirectangular(src, *_FACE_VECTORS[name](a, b))
        yield name, Image.fromarray(output)


def equirectangular_to_cubemap(image: Image.Image, face_size: int) -> dict[str, Image.Image]:
    return dict(iter_cubemap_faces(image, face_size))
