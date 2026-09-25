import time
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connection
from .control_plane import control_plane_status
from .node import get_node_identity

HEARTBEAT_KEY = 'media-engine:worker-heartbeat'


def _check_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        return {'state': 'healthy'}
    except Exception as exc:
        return {'state': 'unhealthy', 'error': str(exc)[:300]}


def _check_cache():
    try:
        key = 'media-engine:health:cache'
        cache.set(key, 'ok', timeout=10)
        ok = cache.get(key) == 'ok'
        return {'state': 'healthy' if ok else 'unhealthy'}
    except Exception as exc:
        return {'state': 'unhealthy', 'error': str(exc)[:300]}


def _check_storage():
    identity = get_node_identity()
    name = f'media_engine/health/{identity.node_id}.txt'
    try:
        stored = default_storage.save(name, ContentFile(b'ok'))
        ok = default_storage.exists(stored)
        default_storage.delete(stored)
        return {'state': 'healthy' if ok else 'unhealthy'}
    except Exception as exc:
        return {'state': 'unhealthy', 'error': str(exc)[:300]}


def _check_worker():
    try:
        stamp = cache.get(HEARTBEAT_KEY)
        if not stamp:
            return {'state': 'degraded', 'reason': 'no_heartbeat'}
        age = max(0, int(time.time() - float(stamp)))
        max_age = int(getattr(settings, 'MEDIA_ENGINE_WORKER_HEARTBEAT_MAX_AGE', 120))
        return {
            'state': 'healthy' if age <= max_age else 'degraded',
            'age_seconds': age,
        }
    except Exception as exc:
        return {'state': 'degraded', 'error': str(exc)[:300]}


def build_health_report(*, deep=False):
    db = _check_database()
    cache_status = _check_cache()
    storage = _check_storage() if deep else {'state': 'healthy', 'check': 'shallow', 'backend': default_storage.__class__.__name__}
    worker = _check_worker()
    control = control_plane_status()
    core_healthy = all(part.get('state') == 'healthy' for part in (db, cache_status, storage))
    state = 'healthy' if core_healthy and worker.get('state') == 'healthy' else ('degraded' if core_healthy else 'unhealthy')
    return {
        'state': state,
        'node': get_node_identity().as_dict(),
        'database': db,
        'cache': cache_status,
        'storage': storage,
        'worker': worker,
        'control_plane': control,
        'control_plane_required_for_runtime': False,
        'deep_storage_check': bool(deep),
    }
