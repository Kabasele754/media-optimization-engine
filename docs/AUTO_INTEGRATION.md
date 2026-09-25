# Automatic integration

For embedded Django installations, add `media_engine` to `INSTALLED_APPS`, migrate, and register the host model fields in settings.

```python
INSTALLED_APPS += ["media_engine"]

MEDIA_ENGINE_TASK_MODE = "auto"
MEDIA_ENGINE_AUTO_FIELDS = {
    "blog.Article": {
        "cover": {"profile": "hero", "role": "hero"},
    },
    "catalog.Product": {
        "photo": {"profile": "card", "role": "content"},
    },
}
```

With `DEBUG=True`, upload processing is inline. With `DEBUG=False`, the same registration queues Celery jobs.

## Automatic discovery

```python
MEDIA_ENGINE_AUTO_DISCOVER_IMAGE_FIELDS = True
```

This is opt-in. Explicit `MEDIA_ENGINE_AUTO_FIELDS` configuration is preferred for production.

## Panorama fields

```python
MEDIA_ENGINE_AUTO_FIELDS = {
    "tours.Scene360": {
        "image_360_original": {
            "profile": "panorama.marzipano",
            "role": "panorama",
        }
    }
}
```

The original remains untouched. MOE creates the preview, cube pyramid, levels and tiles from that original.
