# Testing Media Optimization Engineer in another Django project

A release candidate is reusable only after it passes integration tests in an unrelated Django project with generic models and templates.

## Embedded Django test

1. Create or use an independent Django project.
2. Install a pinned build of media-optimization-engine.
3. Add media_engine to INSTALLED_APPS.
4. Run migrations and media_engine_doctor.
5. Register at least one ImageField with MEDIA_ENGINE_AUTO_FIELDS.
6. Upload a normal image and confirm READY variants.
7. Render the field with the media_image Django tag.
8. Verify AVIF/WebP sources, srcset, sizes, width, height, loading and fetch priority.
9. Verify a missing binding safely falls back to the original field URL.
10. Verify logo/header/footer rendering can use the same registered field without direct .url access.
11. If the project supports 360 media, register one panorama field and confirm multiresolution output.
12. Disable any optional control-plane connection and confirm all local runtime features continue to work.

## Minimum commands

~~~bash
python manage.py migrate
python manage.py media_engine_doctor
python manage.py audit_media_engine
python manage.py audit_panorama_media
~~~

Normal new uploads should process automatically. Backfill and repair commands are for historical or damaged media.

## Template smoke test

~~~django
{% load responsive_media %}

{% media_image article "cover_image"
    alt=article.title
    css_class="article-cover"
    sizes="(max-width: 768px) 100vw, 960px"
%}
~~~

Acceptance criteria:

~~~text
[ ] picture is rendered when a binding exists
[ ] AVIF and/or WebP srcset is present when variants exist
[ ] the nested image keeps the requested CSS class
[ ] width and height are present
[ ] hero role is eager/high priority
[ ] content role is lazy
[ ] fallback still renders when the binding is absent
[ ] no media processing is started from template rendering
[ ] direct derivative URLs are immutable/cacheable
[ ] runtime remains healthy with optional control plane unavailable
~~~
