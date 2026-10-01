# Progressive panorama publication and performance

## Scope and compatibility

This change targets the preparation/delivery pipeline, not an application theme or
viewer framework. It preserves the original upload and the public `build_manifest`,
`to_marzipano`, `generate_all_variants` and model-field integration entry points.
The release candidate is **1.5.0rc1**; creating this branch does not publish PyPI or
container releases. Schema migration `0005_panorama_build_publication` is required.

Old tile rows remain readable through an explicit compatibility path filtered by
processor version. Newly generated panoramas use `PanoramaBuild` revisions. A new
build freezes source hash, algorithm, profile, formats, quality and geometry. Its
URLs include its UUID. Changing configuration or forcing a completed build creates
new URLs rather than overwriting a published asset.

## Publication contract

`PROCESSING -> PREVIEW_READY -> BASE_LEVEL_READY -> READY` are **build** states.
They do not replace the existing `MediaAsset` status vocabulary. `ready=true` means
at least one whole, validated level can be displayed; `complete=true` means the
whole configured pyramid is complete. Readers must not treat `ready` as full HD.

The preview is persisted before tiles. Only contiguous levels with all six cube
faces, exact coordinates, valid dimensions and nonempty storage metadata are
published. During the first import, complete levels become usable progressively.
During regeneration, an already complete revision stays active until the new
revision is fully validated. A failing rebuild does not take it offline.

A database-backed lease is renewed between bounded processing operations. Metadata
publication is fenced by its owner token under a row lock. A worker that outlives
its lease cannot publish over a new owner. This requires a shared transactional
database in multi-worker deployments. SQLite is suitable for unit tests, not a
substitute for production concurrency testing on PostgreSQL. No image bytes are
stored in Redis. Standard derivative locks now use this same fenced lease table.

## Cache and storage

Published descriptors cache storage keys, **not signed URLs**. Cache identities
include database/schema namespace, revision and publication timestamp. A concurrent
reader cannot insert its older snapshot under a newer publication key. Delivery
expands storage URLs afresh. Pending descriptors do not get a one-hour response
cache. The optional `panorama_published` signal is robust and contains identifiers
only; host applications may invalidate their own caches after transaction commit.

The panorama HTTP endpoint uses a private revalidation policy and an ETag. It must
not be confused with image CDN caching. Authorization is still the host's job.
Public immutable `/.../r<uuid>/...` tile URLs may be served with a long cache TTL
and `immutable`. Do **not** apply this to mutable legacy URLs, private responses,
signed links beyond their validity, or tenant-authenticated manifests. Configure
CORS for a separate media origin. Never expose management API credentials to a
browser. This patch does not modify a production bucket/CDN or its access policy.

`build_manifest(asset, profile='panorama.marzipano', compact=True)` returns a compact
URL template only for canonical paths with query-free URLs. Signed or renamed
storage paths retain exact explicit URLs. Both forms pass through `to_marzipano`.
The preview is equirectangular; it is **not** a Marzipano cube preview strip.

## Worker rollout

1. Back up the database; stop/drain old processing workers before schema/code rollout.
2. Install a pinned release/commit of the new engine in web and worker images.
3. Run migrations before starting those workers.
4. Start workers consuming every configured queue, then enable staged processing.
5. Backfill a small batch; inspect completion, image orientation and tile URLs.
6. Enable the updated host viewer. Keep the previous package/images available for rollback.

Recommended configuration (adjust names to existing infrastructure):

```python
MEDIA_ENGINE_TASK_MODE = 'celery'
MEDIA_ENGINE_PANORAMA_STAGED_TASKS = True
MEDIA_ENGINE_PANORAMA_PREVIEW_QUEUE = 'panorama_preview'
MEDIA_ENGINE_PANORAMA_TILES_QUEUE = 'panorama_tiles'
MEDIA_ENGINE_PANORAMA_BACKFILL_QUEUE = 'image_backfill'
MEDIA_ENGINE_PANORAMA_CUBE_MIN_SIZE = 256
MEDIA_ENGINE_PANORAMA_CUBE_MAX_SIZE = 4096
MEDIA_ENGINE_PANORAMA_TILE_SIZE = 512
MEDIA_ENGINE_PANORAMA_CUBE_FORMAT = 'webp'
```

The new queue names are opt-in. Defaults reuse `image_critical`, `image_normal`,
`image_backfill`; heavy non-staged panorama tasks now use the normal queue.
Start tile worker concurrency low and size it using actual peak resident memory.
For example, in the standalone package, consume the configured queues with
`celery -A config worker -Q panorama_preview,panorama_tiles,image_backfill --concurrency=1`.
In an embedded application use that application's Celery app. Independent workers
are preferred to prevent long tile builds delaying previews. If a tenant framework
requires schema activation in tasks, preserve its existing task/context wrapper;
MOE does not select arbitrary host tenants or DB schemas itself.

Preview generation, cube projection and writing reuse source arrays, process bands,
skip complete faces/levels, and batch tile SQL writes. A resumed partial face may be
reprojected, but its completed tiles are not encoded/written again. Bilinear sampling
wraps longitude and clamps latitude. It is a quality change, not a claimed measured
speedup over nearest-neighbor sampling.

## Diagnostics and tests

```bash
python manage.py migrate
python manage.py media_engine_doctor
python manage.py backfill_panorama_media --profile panorama.marzipano --dry-run --limit 5
python manage.py backfill_panorama_media --profile panorama.marzipano --limit 5
python manage.py audit_panorama_media --profile panorama.marzipano --check-files --fail-on-incomplete
python manage.py benchmark_panorama_manifest --asset-id <uuid> --runs 10
DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py test media_engine
```

The benchmark is read-only, aside from warming descriptor cache; it measures
server descriptor/JSON work, not network, browser interaction or GPU timing.
Metrics have bounded labels: panorama stage seconds, tile count/bytes, failures,
and manifest byte size. No user IDs, signed URLs or tenant names appear as labels.

Validate separately on PostgreSQL with concurrent workers, on the chosen object
storage with signed/public URLs, and on real mobile devices. Unit tests do not
establish real-world latency or a guaranteed GPU memory ceiling. Old build files
are deliberately retained; retention/garbage collection must respect active and
rollback references rather than deleting them automatically during this rollout.

## Rollback

Roll back application/worker code together after draining new tasks; do not reverse
the data migration or delete originals automatically. Legacy rows remain. New
revision data requires the new reader, so a code rollback to an older package may
fall back to legacy tiles/originals until it is restored. Keep this tradeoff visible
when selecting the production rollout window.
