# Architecture

Media Optimization Engine supports autonomous per-project nodes.

```text
Project/VPS
  ├─ Django application
  ├─ Media Optimization Engine
  ├─ local database
  ├─ Redis/Celery in production
  ├─ local or S3-compatible storage
  └─ CDN / reverse proxy
```

The optional Ziarama Hub is a control plane only. Runtime upload, processing, manifest generation and derivative delivery do not depend on it.

## Core pipeline

```text
immutable original
      ↓
processor selection
      ├─ standard image → responsive AVIF/WebP/JPEG
      └─ panorama → preview + multires tiles/cubemap
      ↓
manifest
      ↓
direct immutable derivative URLs
```

## Development

With `MEDIA_ENGINE_TASK_MODE=auto` and `DEBUG=True`, processing runs eagerly and Redis/Celery are optional.

## Production

With `DEBUG=False`, auto mode resolves to Celery. Use pinned package versions and persistent storage.
