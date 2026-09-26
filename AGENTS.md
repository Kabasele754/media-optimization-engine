# AGENTS.md — Media Optimization Engineer Integration Contract

This file is the first document an AI coding agent should read before integrating Media Optimization Engineer (MOE) into another application.

## Goal

Connect the current project to MOE through either the embedded Django app or an autonomous local/private node. Runtime media delivery must remain independent from any optional external control plane.

## Non-negotiable invariants

1. Image uploads and reads must continue if an optional control plane is unavailable.
2. Do not call an external control plane from normal request/render paths.
3. Do not store image binaries in Redis.
4. Keep original images as regeneration sources.
5. Public derivatives should use AVIF/WebP plus a fallback and responsive widths.
6. Prefer direct storage/CDN derivative URLs after receiving the manifest.
7. Do not proxy normal image binary delivery through Django views unless explicitly required.
8. Use a pinned MOE version in production; do not use latest.
9. Keep API keys, storage credentials, database credentials and Redis credentials local.
10. Never accept storage/database/API credentials from remote profile configuration.

## Preferred embedded Django integration

Register host model fields:

~~~python
MEDIA_ENGINE_AUTO_FIELDS = {
    "articles.Article": {
        "cover_image": {"profile": "hero", "role": "hero"},
    },
    "accounts.Profile": {
        "photo": {"profile": "avatar", "role": "content"},
    },
}
~~~

Render through Django tags:

~~~django
{% load responsive_media %}

{% media_image article "cover_image"
    alt=article.title
    css_class="article-cover"
    sizes="(max-width: 768px) 100vw, 1200px"
%}
~~~

Do not replace this with manually assembled responsive HTML unless the host project has a specific requirement the tag cannot express.

## Template rendering rules

- Use media_image for a registered model field.
- Use responsive_image when a MediaAsset or MediaBinding is already available.
- Use media_url only when a single URL is necessary.
- Keep image geometry and visual classes on the nested image.
- Use picture_class only for wrapper-specific styling.
- Preserve width and height or a known aspect ratio to reduce layout shift.
- Hero/LCP images should normally use eager loading and high fetch priority.
- Non-critical content should normally remain lazy.
- Do not start ingestion or processing while rendering a template.

## Browser-native responsive selection

For normal HTML, rely on picture/srcset/sizes. The browser already combines rendered width, viewport, DPR, format support and internal network heuristics.

Use JavaScript measurement only for components whose final width cannot be described reliably with sizes, such as a resizable editor, canvas-like builder, or dynamically mounted panel.

## Standalone node discovery

Given an engine base URL, request:

~~~text
GET /.well-known/media-optimization-engine.json
GET /api/v1/system/capabilities/
GET /api/v1/system/version/
GET /api/v1/system/openapi.yaml
~~~

Use /api/v1/system/health/ for operational checks.

## Authentication

Management endpoints may use:

~~~http
Authorization: Bearer <MEDIA_ENGINE_API_KEY>
~~~

Never commit credentials into source control.

## Failure behavior

If a local MOE node is temporarily unavailable during upload, keep the application request recoverable through a clear retry state or locally queued retry work.

If an optional external control plane is unavailable while local processing is healthy, local image processing continues unchanged.

## Acceptance checks

~~~text
[ ] Django field registration succeeds
[ ] normal upload creates READY/PARTIAL derivatives
[ ] media_image renders a responsive picture
[ ] image CSS classes remain on the nested image
[ ] srcset and sizes are present where variants exist
[ ] hero priority is correct
[ ] content images remain lazy
[ ] field URL fallback works before/without a binding
[ ] no template render starts media processing
[ ] direct derivative URL loads
[ ] runtime works with optional control plane disabled
[ ] historical backfill runs independently
~~~

## Panorama rules

Do not crop a 360 equirectangular source as a normal card/hero image.

When the source is known to be 360, use:

- media_kind=panorama
- projection=equirectangular
- profile=panorama.multires

Canonical endpoint:

~~~text
GET /api/v1/images/<id>/panorama/?adapter=generic
~~~

Viewer-specific adapters are available for Pannellum, Marzipano and Three.js. A panorama viewer should request only the levels/tiles needed for the current field of view.
