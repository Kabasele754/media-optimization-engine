# AGENTS.md — Media Optimization Engine Integration Contract

This file is the first document an AI coding agent should read before integrating Media Optimization Engine (MOE) into another application.

## Goal

Connect the current project to a **local/autonomous MOE node** on the same VPS/private network. Do not create a runtime dependency on the Ziarama server or hub.

## Non-negotiable invariants

1. Image uploads and image reads must continue if the Ziarama Hub is unavailable.
2. Do not call the Hub from request/render paths.
3. Do not store image binaries in Redis.
4. Keep original images as regeneration sources.
5. Public derivatives should use AVIF/WebP plus fallback and responsive widths.
6. Prefer direct CDN/Nginx derivative URLs after receiving the manifest.
7. Do not proxy normal image binary delivery through the consuming application's Django views.
8. Use a pinned MOE version in production; do not use `latest`.
9. Keep API keys, storage credentials, database credentials and Redis credentials local to the node.
10. Never accept storage/database/API credentials from remote control-plane profile configuration.

## Discovery

Given an engine base URL, first request:

```text
GET /.well-known/media-optimization-engine.json
```

Then inspect:

```text
GET /api/v1/system/capabilities/
GET /api/v1/system/version/
GET /api/v1/system/openapi.yaml
```

Use `/api/v1/system/health/` for operational checks.

## Authentication

Management endpoints use:

```http
Authorization: Bearer <MEDIA_ENGINE_API_KEY>
```

Never commit the key into source control. Load it from environment/secrets.

## Basic integration sequence

1. Configure a local/private engine URL, e.g. `http://media-engine:8000`.
2. Configure `MEDIA_ENGINE_API_KEY` in the consuming project.
3. On user image upload, send multipart `file`, `profile`, optional `owner_ref`, optional focal coordinates.
4. Store the returned MOE asset UUID with the application's domain object.
5. Poll/retrieve the asset or consume the manifest when status becomes READY/PARTIAL.
6. Render direct manifest URLs with `picture/srcset/sizes` or the native mobile equivalent.
7. For replacement images, create/associate the new asset rather than overwriting immutable derivatives.
8. Backfill historical images through a low-priority queue.

## Required environment variables in a consuming project

```env
MEDIA_ENGINE_URL=http://media-engine:8000
MEDIA_ENGINE_API_KEY=<secret>
MEDIA_ENGINE_DEFAULT_PROFILE=default
```

## Profiles

Use profile names semantically:

- `avatar` for square identity images;
- `card` for list/grid cards;
- `hero` for LCP/large banners;
- `default` for general responsive content.

Do not send arbitrary width transformations when an existing profile fits the UI.

## HTML rendering

For hero/LCP content:

```text
loading=eager
fetchpriority=high
decoding=async
```

For non-critical images:

```text
loading=lazy
decoding=async
```

Always preserve known width/height or aspect ratio to reduce layout shift.

## Failure behavior

If the local MOE node is temporarily unavailable during upload, keep the application request recoverable: return a clear retry state or queue local retry work. Do not fall back to the Ziarama Hub for runtime processing.

If the Hub is unavailable but the local node is healthy, do nothing: this is an expected degraded-control-plane condition and image processing remains local.

## Acceptance checks

Before declaring integration complete:

```text
[ ] well-known discovery succeeds
[ ] API auth rejects bad key
[ ] image upload succeeds
[ ] READY/PARTIAL manifest contains modern formats
[ ] direct derivative URL loads
[ ] hero uses correct priority
[ ] normal cards use lazy loading
[ ] local node still uploads/processes with Hub disabled/unreachable
[ ] node restart works without Hub/registry pull
[ ] historical backfill runs on low-priority queue
```

See `docs/AI_AGENT_INTEGRATION.md` and `docs/TESTING_OTHER_PROJECTS.md` for the full procedure.

## MOE 1.3 panorama integration rules

MOE 1.3 adds a `panorama_360` processor. Do not treat a 360 equirectangular source as a normal card/hero image and do not crop it to 16:9, 4:3 or portrait ratios.

When the source is known to be 360, upload with:

- `media_kind=panorama`
- `projection=equirectangular`
- `profile=panorama.multires`

Canonical panorama endpoint:

`GET /api/v1/images/<id>/panorama/?adapter=generic`

Viewer-specific adapters are available for `pannellum`, `marzipano` and `threejs`. Flutter should consume the generic manifest.

A panorama viewer should not download every high-resolution tile. It should:

1. paint dominant color / preview;
2. choose a level based on viewport and DPR;
3. fetch tiles intersecting the current field of view;
4. prefetch neighboring tiles;
5. promote the visible region to a higher level as needed.

Control-plane rules remain unchanged: Ziarama Hub is never required for runtime image or panorama processing.
