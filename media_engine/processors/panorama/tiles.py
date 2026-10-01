from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image



@dataclass(frozen=True)
class TilePlan:
    level: int
    width: int
    height: int
    cols: int
    rows: int
    tile_size: int


def pyramid_widths(original_width: int, min_width: int = 1024) -> list[int]:
    values = []
    width = max(1, original_width)
    while width > min_width:
        values.append(width)
        width = width // 2
    values.append(min(width, min_width) if original_width >= min_width else original_width)
    return sorted(set(v for v in values if v > 0))


def build_plan(width: int, tile_size: int, level: int) -> TilePlan:
    height = max(1, width // 2)
    return TilePlan(
        level=level,
        width=width,
        height=height,
        cols=math.ceil(width / tile_size),
        rows=math.ceil(height / tile_size),
        tile_size=tile_size,
    )


def generate_level(asset, image: Image.Image, *, profile: str, version: int, plan: TilePlan,
                   fmt: str, quality: int, force=False, build=None, lease=None):
    from .tile_writer import TileWriter
    from .publication import storage_prefix
    writer = TileWriter(asset, profile, version, plan.level, build=build, lease=lease)
    missing = [(col, row) for row in range(plan.rows) for col in range(plan.cols)
        if force or not writer.ready('', col, row, fmt,
            min(plan.tile_size, plan.width - col * plan.tile_size),
            min(plan.tile_size, plan.height - row * plan.tile_size))]
    if not missing:
        return 0
    prefix = storage_prefix(build) if build else (
        f'media_engine/panoramas/{asset.original_sha256[:2]}/{asset.original_sha256}/v{version}/{profile}/')
    work = image.resize((plan.width, plan.height), Image.Resampling.LANCZOS)
    for col, row in missing:
        left, top = col * plan.tile_size, row * plan.tile_size
        right, bottom = min(left + plan.tile_size, plan.width), min(top + plan.tile_size, plan.height)
        writer.write(work.crop((left, top, right, bottom)), face='', col=col, row=row, fmt=fmt,
            quality=quality, level_width=plan.width, level_height=plan.height, prefix=prefix)
    writer.flush()
    work.close()
    return writer.generated
