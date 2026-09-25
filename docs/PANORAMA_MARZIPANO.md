# Marzipano panorama profile

Use profile `panorama.marzipano` for a Marzipano viewer.

The processor builds a cube pyramid. Each level contains faces `f`, `b`, `l`, `r`, `u`, `d`, and each face is split into tiles (512x512 by default).

Recommended settings:

```python
MEDIA_ENGINE_PANORAMA_TILE_SIZE = 512
MEDIA_ENGINE_PANORAMA_CUBE_MIN_SIZE = 512
MEDIA_ENGINE_PANORAMA_CUBE_MAX_SIZE = 4096
MEDIA_ENGINE_PANORAMA_CUBE_FORMAT = "webp"
MEDIA_ENGINE_PANORAMA_CUBE_QUALITY = 72
```

Request:

```text
/api/v1/images/<asset-id>/panorama/?profile=panorama.marzipano&adapter=marzipano
```

The response contains `geometry.levels` and explicit `tiles`. A client builds a tile lookup using `(z, face, x, y)`.
