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


def _sample_equirectangular(array: np.ndarray, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    norm = np.sqrt(x * x + y * y + z * z)
    x, y, z = x / norm, y / norm, z / norm
    lon = np.arctan2(x, z)
    lat = np.arcsin(np.clip(y, -1.0, 1.0))
    h, w = array.shape[:2]
    px = ((lon / (2.0 * math.pi)) + 0.5) * (w - 1)
    py = (0.5 - lat / math.pi) * (h - 1)
    xi = np.mod(np.rint(px).astype(np.int64), w)
    yi = np.clip(np.rint(py).astype(np.int64), 0, h - 1)
    return array[yi, xi]


def equirectangular_to_cubemap(image: Image.Image, face_size: int) -> dict[str, Image.Image]:
    src = np.asarray(image.convert('RGB'))
    axis = np.linspace(-1.0, 1.0, face_size, dtype=np.float32)
    a, b = np.meshgrid(axis, -axis)
    result = {}
    for name, vector_fn in _FACE_VECTORS.items():
        x, y, z = vector_fn(a, b)
        sampled = _sample_equirectangular(src, x, y, z)
        result[name] = Image.fromarray(sampled.astype(np.uint8), mode='RGB')
    return result
