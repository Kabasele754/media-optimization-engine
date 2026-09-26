# Django integration

Media Optimization Engineer is designed first as a Django/Python package. The recommended integration path uses registered model fields and Django template tags rather than hand-written responsive HTML.

## 1. Install and register

~~~bash
pip install media-optimization-engine
~~~

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
        "thumbnail": {
            "profile": "card",
            "role": "content",
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

~~~bash
python manage.py migrate
python manage.py media_engine_doctor
~~~

With MEDIA_ENGINE_TASK_MODE set to auto, local development runs inline when DEBUG is true and production can queue work through Celery when DEBUG is false.

## 2. Render an ImageField from a model

Use the model instance and field name directly:

~~~django
{% load responsive_media %}

{% media_image article "cover_image"
    alt=article.title
    css_class="article-detail__hero"
    sizes="(max-width: 768px) 100vw, min(1200px, 92vw)"
%}
~~~

The tag:

1. resolves the MediaBinding for article.cover_image;
2. uses the configured profile and role;
3. emits available AVIF/WebP responsive sources;
4. keeps CSS presentation classes on the nested image;
5. preserves width and height to reduce layout shift;
6. falls back to the original field URL only when no usable binding exists.

Template rendering never ingests or processes media synchronously.

## 3. Hero/LCP image

A registered field with role hero automatically receives eager loading and high fetch priority unless explicitly overridden:

~~~django
{% load responsive_media %}

{% media_image article "cover_image"
    alt=article.title
    role="hero"
    css_class="article-hero"
    picture_class="article-hero-picture"
    sizes="100vw"
%}
~~~

The image class belongs to the nested image. Wrapper-only layout hooks belong in picture_class.

## 4. Grid and card images

~~~django
{% load responsive_media %}

<section class="article-grid">
  {% for article in articles %}
    <article class="article-card">
      {% media_image article "thumbnail"
          alt=article.title
          css_class="article-card__image"
          sizes="(max-width: 640px) 92vw, (max-width: 1100px) 45vw, 360px"
      %}
      <h2>{{ article.title }}</h2>
    </article>
  {% endfor %}
</section>
~~~

## 5. Logos, headers, and footers

Treat logos as normal registered model fields. Do not bypass MOE with organization.logo.url in templates when optimized output is desired.

~~~django
{% load responsive_media %}

<header class="site-header">
  {% media_image organization "logo"
      alt=organization.name
      css_class="site-header__logo"
      sizes="220px"
  %}
</header>

<footer class="site-footer">
  {% media_image organization "logo"
      alt=organization.name
      css_class="site-footer__logo"
      sizes="180px"
  %}
</footer>
~~~

The same field can therefore be used in multiple layout contexts while the browser selects the most suitable derivative.

## 6. Direct MediaAsset rendering

When application code already has a MediaBinding or MediaAsset:

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

## 7. Obtain one optimized URL

Use media_url only when a single URL is required, such as metadata, email templates, CSS variables, or JSON responses:

~~~django
{% load responsive_media %}

{% media_url organization "logo"
    preferred_width=512
    preferred_format="webp"
    as optimized_logo
%}

<meta property="og:image" content="{{ optimized_logo }}">
~~~

For normal page images, media_image is preferred because srcset and sizes allow the browser to account for actual layout and DPR.

## 8. CSS migration contract

If an existing template used:

~~~django
<img src="{{ article.cover_image.url }}" class="article-image" alt="{{ article.title }}">
~~~

replace it with:

~~~django
{% load responsive_media %}

{% media_image article "cover_image"
    alt=article.title
    css_class="article-image"
%}
~~~

Keep the original image class. If legacy CSS uses a direct-child selector such as:

~~~css
.card > img {
  width: 100%;
}
~~~

bridge it during migration:

~~~css
.card > img,
.card > picture > img {
  width: 100%;
}
~~~

Do not move image geometry, object-fit, border radius, or transforms from the image to the picture wrapper unless the design explicitly requires wrapper styling.

## 9. Browser-native adaptive selection

For standard web pages, no JavaScript is required. The generated picture/srcset/sizes structure lets the browser choose based on:

- rendered layout width;
- viewport;
- device pixel ratio;
- supported format;
- browser/network heuristics.

Declare realistic sizes in the Django tag:

~~~django
{% media_image product "photo"
    alt=product.name
    css_class="product-card__photo"
    sizes="(max-width: 600px) 94vw, (max-width: 1024px) 46vw, 320px"
%}
~~~

Runtime JavaScript measurement should be reserved for components whose dimensions cannot be expressed reliably with sizes, such as resizable editors or dynamically mounted canvases.

## 10. Historical backfill

~~~bash
python manage.py backfill_registered_media
python manage.py audit_media_engine --fail-on-incomplete
~~~

Backfill is a maintenance operation. Normal new uploads registered in MEDIA_ENGINE_AUTO_FIELDS should not require repair commands.

## 11. Standalone node mode

Projects that do not embed the Django app can use the REST API and manifest endpoints. They should still render browser-native responsive images or equivalent native-client selection from the manifest.

Optional control-plane synchronization is never part of the normal request/render path.
