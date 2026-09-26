# Architecture

Media Optimization Engineer supports two autonomous deployment modes:

~~~text
Embedded Django application
  ├─ host Django project
  ├─ media_engine Django app
  ├─ database
  ├─ optional Redis/Celery
  ├─ local or object storage
  └─ optional CDN / reverse proxy
~~~

~~~text
Standalone node
  ├─ Media Optimization Engineer API
  ├─ database
  ├─ Redis/Celery in production
  ├─ local or object storage
  └─ optional CDN / reverse proxy
~~~

An optional external control plane may synchronize non-secret profile configuration, but runtime upload, processing, manifest generation, rendering, and derivative delivery remain autonomous.

## Core image pipeline

~~~text
immutable original
      ↓
ingest + validation
      ↓
semantic profile
      ↓
processor
      ├─ standard image → responsive AVIF/WebP/JPEG variants
      └─ panorama → preview + multiresolution tiles/cubemap
      ↓
manifest
      ↓
Django template tags / REST clients
      ↓
direct immutable derivative URLs
~~~

## Django rendering boundary

The public Django API is the template-tag layer:

~~~django
{% load responsive_media %}

{% media_image object "image_field"
    alt=object.title
    css_class="content-image"
    sizes="100vw"
%}
~~~

The renderer never starts image processing during a template request. It resolves an existing MediaBinding and renders available derivatives. When no binding is ready, it preserves page availability with the field's current URL.

## Responsive selection

For normal HTML, the browser is the final selector. MOE generates width descriptors and sizes; the browser combines them with layout width, viewport, DPR, format support, and its own resource-selection heuristics.

JavaScript is an optional enhancement for highly dynamic components, not a requirement for standard responsive images.

## Development

With MEDIA_ENGINE_TASK_MODE=auto and DEBUG=True, processing can run eagerly and Redis/Celery are optional.

## Production

With DEBUG=False, auto mode resolves to Celery. Pin package versions, use persistent storage, and serve immutable derivatives directly from storage/CDN whenever possible.
