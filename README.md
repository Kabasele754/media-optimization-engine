# Media Optimization Engine 1.4.0

Media Optimization Engine (MOE) is an extensible media-processing package for Django applications and autonomous media nodes. Version 1.3 adds a dedicated 360 panorama pipeline with multiresolution tiling inspired by map viewers: a low-resolution representation can appear immediately while only the visible high-resolution tiles are fetched.

## What this release handles

### Standard images

- AVIF and WebP derivatives;
- responsive widths;
- JPEG fallback;
- smart focal point support;
- dominant color, BlurHash and lightweight placeholders;
- SHA-256 deduplication;
- local, S3-compatible and Cloudflare R2 storage;
- Redis locks/cache and Celery processing when enabled;
- CDN-ready fingerprinted derivative paths.

### 360 panoramas

- equirectangular 2:1 panorama detection;
- explicit `media_kind=panorama` support;
- progressive preview;
- multiresolution pyramid;
- 512x512 AVIF/WebP tiles;
- generic viewer-independent manifest;
- Pannellum adapter;
- Marzipano adapter;
- Three.js adapter;
- Flutter manifest reference models;
- optional cubemap generation;
- audit and backfill commands.

## Panorama example

An 8192x4096 panorama becomes:

```
L0  1024x512
L1  2048x1024
L2  4096x2048
L3  8192x4096
```

Each level is tiled. A viewer can display the preview or L0 immediately, request visible L1/L2 tiles while the camera moves, and request L3 only for the active field of view or zoomed areas.

## Install

```bash
pip install media-optimization-engine
```

For infrastructure extras:

```bash
pip install "media-optimization-engine[all]==1.4.0"
```

## Django integration

```python
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "media_engine",
]
```

Include the URLs:

```python
path("api/v1/", include("media_engine.urls")),
```

Then:

```bash
python manage.py migrate
python manage.py media_engine_doctor
```

## Automatic Django integration

Normal uploads do not require manual backfill/repair commands. Configure fields once with `MEDIA_ENGINE_AUTO_FIELDS`. With `MEDIA_ENGINE_TASK_MODE="auto"`, development runs inline when `DEBUG=True`, while production queues Celery when `DEBUG=False`.

## Node autonomy

The Ziarama Hub is optional. Processing, storage, Redis, Celery and media delivery stay local to each node.

## License

MIT License. Copyright (c) 2026 Achilles Kabasele.
