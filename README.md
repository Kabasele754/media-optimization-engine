# Media Optimization Engineer 1.4

Media Optimization Engineer (MOE) is a reusable Django/Python package for image optimization, responsive delivery, and 360-degree media processing.

The public package is intentionally application-agnostic. It does not depend on any consuming project's themes, tenants, brands, business models, or private infrastructure.

## Core capabilities

### Standard images

- automatic ImageField / FileField integration;
- immutable originals;
- AVIF, WebP and JPEG derivatives;
- responsive width sets;
- semantic profiles such as avatar, card, hero, and default;
- focal-point aware crops;
- dominant color, BlurHash and lightweight placeholders;
- SHA-256 deduplication;
- local, S3-compatible and Cloudflare R2 storage;
- Redis/Celery processing when enabled;
- CDN-ready derivative URLs;
- Django template tags for responsive rendering.

### 360 panoramas

- equirectangular panorama support;
- progressive preview;
- multiresolution pyramids;
- tiled AVIF/WebP delivery;
- generic manifests;
- Pannellum, Marzipano and Three.js adapters;
- optional cubemap generation.

## Install

~~~bash
pip install media-optimization-engine
~~~

Optional infrastructure extras:

~~~bash
pip install "media-optimization-engine[all]"
~~~

## Django setup

~~~python
# settings.py
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "media_engine",
]

MEDIA_ENGINE_TASK_MODE = "auto"

MEDIA_ENGINE_AUTO_FIELDS = {
    "articles.Article": {
        "cover_image": {
            "profile": "hero",
            "role": "hero",
        },
    },
    "accounts.Profile": {
        "photo": {
            "profile": "avatar",
            "role": "content",
        },
    },
    "organizations.Organization": {
        "logo": {
            "profile": "default",
            "role": "content",
        },
    },
}
~~~

~~~python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("media_engine.urls")),
]
~~~

Then:

~~~bash
python manage.py migrate
python manage.py media_engine_doctor
~~~

## Django template rendering

For normal model fields, use the high-level media_image tag:

~~~django
{% load responsive_media %}

{% media_image article "cover_image"
    alt=article.title
    css_class="article-hero"
    sizes="(max-width: 768px) 100vw, 1200px"
%}
~~~

MOE resolves the field's MediaBinding, generates a responsive picture with available AVIF/WebP sources, preserves the image's CSS classes, and falls back to the original field URL only when no processed binding is available.

### Logo or footer image

~~~django
{% load responsive_media %}

{% media_image organization "logo"
    alt=organization.name
    css_class="site-logo"
    sizes="240px"
%}
~~~

### Card grid

~~~django
{% load responsive_media %}

{% for article in articles %}
  <article class="article-card">
    {% media_image article "cover_image"
        alt=article.title
        css_class="article-card__image"
        sizes="(max-width: 640px) 92vw, (max-width: 1100px) 45vw, 360px"
    %}
    <h2>{{ article.title }}</h2>
  </article>
{% endfor %}
~~~

### Direct binding rendering

Advanced integrations can render a known asset directly:

~~~django
{% load responsive_media %}

{% responsive_image binding.asset
    profile=binding.profile
    role=binding.role
    alt=object.title
    css_class="media-object"
    picture_class="media-object-picture"
    sizes="100vw"
%}
~~~

### One optimized URL

For Open Graph metadata, CSS backgrounds, emails, or APIs where picture is not possible:

~~~django
{% load responsive_media %}

{% media_url organization "logo" preferred_width=512 preferred_format="webp" as optimized_logo %}

<meta property="og:image" content="{{ optimized_logo }}">
~~~

For normal page images, prefer media_image over media_url; the browser can make a better final choice from srcset and sizes.

## Responsive selection

MOE provides width descriptors and sizes. The browser chooses the final resource using layout width, viewport, DPR, supported formats, and its own network heuristics.

JavaScript is not required for normal responsive images.

Runtime measurement is appropriate only for highly dynamic components whose rendered width cannot be described reliably with sizes, such as resizable editors, canvas-like builders, or asynchronously mounted panels.

## Backfill

Historical media can be ingested with maintenance commands:

~~~bash
python manage.py backfill_registered_media
python manage.py audit_media_engine --fail-on-incomplete
~~~

New uploads registered in MEDIA_ENGINE_AUTO_FIELDS are handled automatically.

## Runtime independence

Embedded Django mode and standalone-node mode are autonomous. Optional control-plane synchronization must never be required for upload, processing, rendering, or derivative delivery.

## License

MIT License. Copyright (c) 2026 Achille Kabasele.
