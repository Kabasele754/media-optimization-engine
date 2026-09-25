# Testing MOE in another Django project

The package is considered reusable only after it works outside Ziarama.

## Embedded test

1. Create or use an unrelated Django project.
2. Install a pinned build of `media-optimization-engine`.
3. Add `media_engine` to `INSTALLED_APPS`.
4. Run migrations and `media_engine_doctor`.
5. Register one normal `ImageField` with `MEDIA_ENGINE_AUTO_FIELDS`.
6. Upload one normal image and confirm READY variants.
7. If the project supports 360 media, register one panorama field and confirm multires tiles.
8. Verify the host project still runs when the optional Ziarama Hub is disabled.

## Minimum commands

```bash
python manage.py migrate
python manage.py media_engine_doctor
python manage.py audit_media_engine
python manage.py audit_panorama_media
```

Normal new uploads should process automatically. Backfill/repair commands are only for historical or damaged media.
