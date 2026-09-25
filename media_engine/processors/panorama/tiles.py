from __future__ import annotations

import io
import math
from dataclasses import dataclass

from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from ...image_ops import encode_with_budget
from ...models import PanoramaTile


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


def generate_level(asset, image: Image.Image, *, profile: str, version: int, plan: TilePlan, fmt: str, quality: int, force: bool = False):
    work = image.resize((plan.width, plan.height), Image.Resampling.LANCZOS)
    generated = 0
    for row in range(plan.rows):
        for col in range(plan.cols):
            left = col * plan.tile_size
            top = row * plan.tile_size
            right = min(left + plan.tile_size, plan.width)
            bottom = min(top + plan.tile_size, plan.height)
            tile = work.crop((left, top, right, bottom))
            obj, _ = PanoramaTile.objects.get_or_create(
                asset=asset,
                profile=profile,
                processor_version=version,
                level=plan.level,
                face='',
                col=col,
                row=row,
                format=fmt,
                defaults={'width': tile.width, 'height': tile.height},
            )
            if obj.status == PanoramaTile.Status.READY and not force:
                continue
            encoded = encode_with_budget(tile, fmt, quality, target_bytes=None)
            path = (
                f'media_engine/panoramas/{asset.original_sha256[:2]}/'
                f'{asset.original_sha256}/v{version}/{profile}/'
                f'l{plan.level}/{col}_{row}.{fmt}'
            )
            if default_storage.exists(path):
                default_storage.delete(path)
            stored = default_storage.save(path, ContentFile(encoded.content))
            obj.file = stored
            obj.width = tile.width
            obj.height = tile.height
            obj.file_size = len(encoded.content)
            obj.quality = encoded.quality
            obj.status = PanoramaTile.Status.READY
            obj.last_error = ''
            obj.save()
            generated += 1
    return generated
