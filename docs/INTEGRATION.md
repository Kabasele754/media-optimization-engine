# Integration Into Another Project

There are two supported integration modes.

## Mode A — local sidecar node

Use this when the target project already has its own VPS or Docker stack.

```text
Target project
   |
   +-- app
   +-- postgres
   +-- redis
   +-- media-engine node
   +-- media worker
```

The project calls the node over a private network, stores the returned asset UUID and renders direct manifest URLs.

Environment:

```env
MEDIA_ENGINE_URL=http://media-engine:8000
MEDIA_ENGINE_API_KEY=<secret>
```

## Mode B — embedded Django app

```bash
pip install media-optimization-engine
```

```python
INSTALLED_APPS += ['rest_framework', 'media_engine']
```

Add URLs:

```python
path('api/v1/', include('media_engine.urls')),
```

Then:

```bash
python manage.py migrate
python manage.py media_engine_doctor
```

### Automatic host-field integration

```python
MEDIA_ENGINE_TASK_MODE = "auto"
MEDIA_ENGINE_AUTO_FIELDS = {
    "catalog.Product": {
        "photo": {"profile": "card", "role": "content"},
    },
    "tours.Scene360": {
        "image_360_original": {"profile": "panorama.marzipano", "role": "panorama"},
    },
}
```

In local development with `DEBUG=True`, processing is eager and does not require a Celery worker. In production with `DEBUG=False`, processing is queued through Celery.

### Backfill

Backfill commands are maintenance tools for historical media, not part of the normal upload path:

```bash
python manage.py backfill_registered_media
python manage.py audit_media_engine --fail-on-incomplete
```

### Template rendering

```django
{% load responsive_media %}
{% responsive_image binding.asset profile=binding.profile role=binding.role alt=object.name %}
```

When replacing an existing `<img>` with MOE, keep its presentation contract on the nested image. Pass the old CSS classes through `css_class`, and pass inline geometry/crop rules through `style`. Use `picture_class` only for wrapper-specific styling:

```django
{% responsive_image binding.asset profile=binding.profile css_class="tenant-logo" picture_class="media-picture tenant-logo" style="object-fit:contain" %}
```

The `<picture>` element selects the optimized file; the nested `<img>` remains the replaced element that owns dimensions, object-fit, border radius, transforms, and other image presentation rules. Host applications with legacy direct-child selectors such as `.card > img` should bridge them to `.card > picture > img` during migration rather than dropping the original design.

Only the true hero/LCP image should be eager. Non-critical content remains lazy.

## Flutter / mobile

Use the manifest endpoint and select a suitable width from logical display width × DPR. Cache immutable URLs aggressively.

## Control-plane rule

The optional Ziarama Hub is never part of the normal request path. A target project must continue processing media when the Hub is disabled or unreachable.
