from django.conf import settings


def resolved_task_mode():
    """Return the effective execution mode without requiring Docker/Redis locally."""
    configured = str(getattr(settings, 'MEDIA_ENGINE_TASK_MODE', 'auto') or 'auto').lower()
    if configured in {'eager', 'inline', 'sync', 'synchronous'}:
        return 'eager'
    if configured in {'celery', 'async', 'asynchronous'}:
        return 'celery'
    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        return 'eager'
    return 'eager' if bool(getattr(settings, 'DEBUG', False)) else 'celery'


def queue_for_profile(profile, backfill=False):
    if backfill:
        return 'image_backfill'
    if profile == 'hero' or profile.startswith('panorama.'):
        return 'image_critical'
    return 'image_normal'


def enqueue_asset(asset_id, profile='default', force=False, backfill=False):
    if resolved_task_mode() == 'eager':
        from .models import MediaAsset
        from .services import generate_all_variants
        asset = MediaAsset.objects.get(pk=asset_id)
        return generate_all_variants(asset, profile_name=profile, force=force)
    from .tasks import generate_asset_variants
    return generate_asset_variants.apply_async(
        args=[str(asset_id), profile, force],
        queue=queue_for_profile(profile, backfill=backfill),
    )
