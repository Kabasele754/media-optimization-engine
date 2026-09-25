# Media Optimization Engine 1.4.0rc2

## Auto Integration & Publishing Edition

Version 1.4.0rc2 makes the package easier to install in unrelated Django projects and removes the need for manual processing commands in the normal upload path.

### Automatic runtime mode

`MEDIA_ENGINE_TASK_MODE="auto"` is the recommended default:

- `DEBUG=True` -> inline/eager generation;
- `DEBUG=False` -> Celery generation.

### Portable model integration

Host projects may register fields through settings:

```python
MEDIA_ENGINE_AUTO_FIELDS = {
    "catalog.Product": {
        "photo": {"profile": "card", "role": "content"},
    },
    "tours.Scene360": {
        "image_360_original": {"profile": "panorama.marzipano", "role": "panorama"},
    },
}
```

Optional whole-project ImageField discovery is available through `MEDIA_ENGINE_AUTO_DISCOVER_IMAGE_FIELDS=True`, but remains disabled by default.

### Packaging

- Author/Maintainer: Achille Kabasele
- Email: pepexykabasele@gmail.com
- License: MIT
- CLI: `media-engine-doctor`
- PyPI/TestPyPI Trusted Publishing workflows

### 360

Multiresolution equirectangular and Marzipano cube pipelines are supported. Originals remain immutable sources of truth.
