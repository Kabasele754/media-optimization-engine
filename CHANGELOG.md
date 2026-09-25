# Changelog

## 1.4.0rc3 - 2026-09-25
- Broadened runtime compatibility for existing Django 4.2.30 / DRF 3.14 / Pillow 10.3 projects while keeping Django 5.2+ support.
- Added automatic host-field registration through `MEDIA_ENGINE_AUTO_FIELDS`.
- Added optional ImageField discovery for controlled migrations.
- Added `MEDIA_ENGINE_TASK_MODE=auto`: eager in DEBUG, Celery in production.
- Prevented unchanged bindings from triggering unnecessary regeneration.
- Added `media-engine-doctor` console entrypoint.
- Added TestPyPI/PyPI Trusted Publishing workflows and machine-readable integration context YAML.
- Updated package metadata for Achille Kabasele and MIT licensing.

## 1.3.2
- Added Marzipano-compatible multiresolution cubemap panorama pipeline.
- Added `PanoramaTile.face` and migration `0003_panorama_cube_tiles`.
- Added `panorama.marzipano` / `panorama.cube` profiles with progressive CubeGeometry tiles.
- Marzipano adapter exposes explicit tile URLs, preserving compatibility with local storage, S3 and R2.

## 1.3.1
- Added integration doctor management command.
- Added standalone Django consumer smoke project.
- Documented embedded Django installation contract.
- Added author and MIT metadata.

## 1.3.0 - Panorama Multires
- Added processor registry and media-kind dispatch.
- Added equirectangular panorama detection.
- Added multiresolution panorama pyramid and 512x512 AVIF/WebP tiles.
- Added panorama preview and generic manifest.
- Added optional cubemap conversion.
- Added Pannellum, Marzipano, Three.js and Flutter adapters.
- Added `audit_panorama_media` and `backfill_panorama_media`.
- Added `PanoramaTile` persistence and migration.

## 1.1.0 - Distributed Nodes
- Autonomous nodes, last-known-good control-plane configuration, API-key auth, discovery, failover documentation and publishing workflow.
