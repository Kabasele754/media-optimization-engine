from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image

from .cubemap import iter_cubemap_faces

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
    if any(v < 16 or v & (v - 1) for v in (min_size, max_size)) or max_size < min_size:
        raise ValueError('Cubemap bounds must be ordered powers of two >= 16')
    # A common equirectangular panorama has width ~= 4 * cubemap face width.
    estimated = max(min_size, int(original_width / 4))
    top = _largest_power_of_two_lte(estimated, minimum=min_size, maximum=max_size)
    sizes: list[int] = []
    current = min_size
    while current <= top:
        sizes.append(current)
        current *= 2
    return sizes or [min_size]


def generate_cube_level(asset, source_image: Image.Image, *, profile: str, version: int,
                        plan: CubeLevelPlan, fmt='webp', quality=72, force=False,
                        build=None, lease=None, source_array=None) -> int:
    from .tile_writer import TileWriter
    from .publication import storage_prefix
    writer = TileWriter(asset, profile, version, plan.level, build=build, lease=lease)
    missing_faces = []
    for name, face in FACE_NAME_TO_KEY.items():
        if any(force or not writer.ready(face, col, row, fmt,
                    min(plan.tile_size, plan.size - col * plan.tile_size),
                    min(plan.tile_size, plan.size - row * plan.tile_size))
               for row in range(plan.rows) for col in range(plan.cols)):
            missing_faces.append(name)
    if not missing_faces:
        return 0  # No projection, source decode or storage HEAD for completed levels.
    prefix = storage_prefix(build) if build else (
        f'media_engine/panoramas/{asset.original_sha256[:2]}/{asset.original_sha256}/v{version}/{profile}/')
    for name, face_image in iter_cubemap_faces(source_image, plan.size, faces=missing_faces,
            checkpoint=lease.checkpoint if lease else None, source_array=source_array):
        face = FACE_NAME_TO_KEY[name]
        for row in range(plan.rows):
            for col in range(plan.cols):
                left, top = col * plan.tile_size, row * plan.tile_size
                right, bottom = min(left + plan.tile_size, plan.size), min(top + plan.tile_size, plan.size)
                if not force and writer.ready(face, col, row, fmt, right-left, bottom-top):
                    continue
                writer.write(face_image.crop((left, top, right, bottom)), face=face, col=col, row=row,
                    fmt=fmt, quality=quality, level_width=plan.size, level_height=plan.size, prefix=prefix)
        writer.flush()
        face_image.close()
    return writer.generated
