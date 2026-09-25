from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from ...image_ops import encode_with_budget
from ...models import PanoramaTile
from .cubemap import equirectangular_to_cubemap

# Marzipano's CubeGeometry canonical face keys.
FACE_NAME_TO_KEY = {
    'front': 'f',
    'back': 'b',
    'left': 'l',
    'right': 'r',
    'top': 'u',
    'bottom': 'd',
}


@dataclass(frozen=True)
class CubeLevelPlan:
    level: int
    size: int
    tile_size: int

    @property
    def cols(self) -> int:
        return math.ceil(self.size / self.tile_size)

    @property
    def rows(self) -> int:
        return math.ceil(self.size / self.tile_size)


def _largest_power_of_two_lte(value: int, *, minimum: int = 512, maximum: int = 4096) -> int:
    value = min(max(int(value), minimum), maximum)
    power = 1
    while power * 2 <= value:
        power *= 2
    return max(power, minimum)


def cube_level_sizes(original_width: int, *, min_size: int = 512, max_size: int = 4096) -> list[int]:
    # A common equirectangular panorama has width ~= 4 * cubemap face width.
    estimated = max(min_size, int(original_width / 4))
    top = _largest_power_of_two_lte(estimated, minimum=min_size, maximum=max_size)
    sizes: list[int] = []
    current = min_size
    while current <= top:
        sizes.append(current)
        current *= 2
    return sizes or [min_size]


def generate_cube_level(
    asset,
    source_image: Image.Image,
    *,
    profile: str,
    version: int,
    plan: CubeLevelPlan,
    fmt: str = 'webp',
    quality: int = 72,
    force: bool = False,
) -> int:
    faces = equirectangular_to_cubemap(source_image, plan.size)
    generated = 0
    for face_name, face_image in faces.items():
        face = FACE_NAME_TO_KEY[face_name]
        for row in range(plan.rows):
            for col in range(plan.cols):
                left = col * plan.tile_size
                top = row * plan.tile_size
                right = min(left + plan.tile_size, plan.size)
                bottom = min(top + plan.tile_size, plan.size)
                tile = face_image.crop((left, top, right, bottom))
                obj, _ = PanoramaTile.objects.get_or_create(
                    asset=asset,
                    profile=profile,
                    processor_version=version,
                    level=plan.level,
                    face=face,
                    col=col,
                    row=row,
                    format=fmt,
                    defaults={
                        'width': tile.width,
                        'height': tile.height,
                        'level_width': plan.size,
                        'level_height': plan.size,
                    },
                )
                if obj.status == PanoramaTile.Status.READY and not force:
                    continue
                encoded = encode_with_budget(tile, fmt, quality, target_bytes=None)
                path = (
                    f'media_engine/panoramas/{asset.original_sha256[:2]}/'
                    f'{asset.original_sha256}/v{version}/{profile}/'
                    f'l{plan.level}/{face}/{col}_{row}.{fmt}'
                )
                if default_storage.exists(path):
                    default_storage.delete(path)
                stored = default_storage.save(path, ContentFile(encoded.content))
                obj.file = stored
                obj.width = tile.width
                obj.height = tile.height
                obj.level_width = plan.size
                obj.level_height = plan.size
                obj.file_size = len(encoded.content)
                obj.quality = encoded.quality
                obj.status = PanoramaTile.Status.READY
                obj.last_error = ''
                obj.save()
                generated += 1
    return generated
