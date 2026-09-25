from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from datetime import timedelta
from .models import MediaAsset, MediaVariant
from .services import generate_all_variants


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def generate_asset_variants(self, asset_id, profile='default', force=False):
    asset = MediaAsset.objects.get(pk=asset_id)
    generate_all_variants(asset, profile_name=profile, force=force)
    return str(asset.id)


@shared_task
def cleanup_orphan_derivatives_task(days=30):
    threshold = timezone.now() - timedelta(days=days)
    current_version = getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)
    qs = MediaVariant.objects.filter(processor_version__lt=current_version, updated_at__lt=threshold)
    removed = 0
    for variant in qs.iterator():
        if variant.file and default_storage.exists(variant.file.name):
            default_storage.delete(variant.file.name)
        variant.delete()
        removed += 1
    return removed


@shared_task
def worker_heartbeat_task():
    import time
    from django.core.cache import cache
    from .health import HEARTBEAT_KEY
    stamp = time.time()
    cache.set(HEARTBEAT_KEY, stamp, timeout=300)
    return stamp


@shared_task
def sync_control_plane_config_task():
    from .control_plane import sync_from_control_plane
    return sync_from_control_plane(force=False)
