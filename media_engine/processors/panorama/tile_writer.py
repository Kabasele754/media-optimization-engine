"""Write only missing tiles into an immutable generation namespace."""
from contextlib import nullcontext

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from ...image_ops import encode_with_budget
from ...models import PanoramaTile
from ...metrics import PANORAMA_TILES_GENERATED, PANORAMA_BYTES_WRITTEN


class TileWriter:
    def __init__(self, asset, profile, version, level, build=None, lease=None):
        self.asset, self.profile, self.version, self.level = asset, profile, version, level
        self.build, self.lease = build, lease
        self.using = asset._state.db or 'default'
        self.existing = {(t.face, t.col, t.row, t.format): t for t in PanoramaTile.objects.using(self.using).filter(
            asset=asset, profile=profile, processor_version=version, level=level, build=build)}
        self.new, self.changed = [], []
        self.generated = 0

    def ready(self, face, col, row, fmt, width, height):
        tile = self.existing.get((face, col, row, fmt))
        return bool(tile and tile.status == 'READY' and tile.file and tile.file_size > 0
                    and (tile.width, tile.height) == (width, height))

    def write(self, image, *, face, col, row, fmt, quality, level_width, level_height, prefix):
        if self.lease:
            self.lease.checkpoint()
        encoded = encode_with_budget(image, fmt, quality, target_bytes=None)
        if self.lease:
            self.lease.checkpoint(force=True)
        path = f'{prefix}l{self.level}/' + (f'{face}/' if face else '') + f'{col}_{row}.{fmt}'
        # Never delete/overwrite a published URL. Storage may choose another name
        # after a crash; the explicit snapshot records its exact return value.
        stored = default_storage.save(path, ContentFile(encoded.content))
        tile = self.existing.get((face, col, row, fmt))
        is_new = tile is None
        if tile is None:
            tile = PanoramaTile(asset=self.asset, profile=self.profile, processor_version=self.version,
                build=self.build, level=self.level, face=face, col=col, row=row, format=fmt)
        tile.file = stored
        tile.width, tile.height = image.size
        tile.level_width, tile.level_height = level_width, level_height
        tile.file_size, tile.quality = len(encoded.content), encoded.quality
        tile.status, tile.last_error = 'READY', ''
        tile.updated_at = timezone.now()
        (self.new if is_new else self.changed).append(tile)
        self.existing[(face, col, row, fmt)] = tile
        self.generated += 1
        PANORAMA_TILES_GENERATED.labels(format=fmt).inc()
        PANORAMA_BYTES_WRITTEN.labels(format=fmt).inc(len(encoded.content))
        if len(self.new) + len(self.changed) >= 32:
            self.flush()

    def flush(self):
        if not self.new and not self.changed:
            return
        with self.lease.guard() if self.lease else nullcontext():
            manager = PanoramaTile.objects.using(self.using)
            if self.new:
                manager.bulk_create(self.new, batch_size=32)
            if self.changed:
                manager.bulk_update(self.changed, ['file', 'width', 'height', 'level_width', 'level_height',
                    'file_size', 'quality', 'status', 'last_error', 'updated_at'], batch_size=32)
        self.new.clear()
        self.changed.clear()
