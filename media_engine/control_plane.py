"""Optional Ziarama control-plane integration.

Runtime image processing NEVER calls the control plane. This module is invoked only
by an explicit management command or a background Celery sync task. The engine
always uses local settings plus the last-known-good local snapshot.
"""

import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.cache import cache

from .node import get_node_identity

STATUS_CACHE_KEY = 'media-engine:control-plane:status'
CIRCUIT_CACHE_KEY = 'media-engine:control-plane:circuit-open-until'
CONFIG_CACHE_KEY = 'media-engine:control-plane:last-known-good'
_ALLOWED_FORMATS = {'avif', 'webp', 'jpeg', 'jpg'}
_ALLOWED_FITS = {'contain', 'cover'}


def _config_dir() -> Path:
    return Path(getattr(settings, 'MEDIA_ENGINE_CONFIG_DIR', '/var/lib/media-engine/config'))


def _path(name: str) -> Path:
    return _config_dir() / name


def _safe_cache_get(key, default=None):
    try:
        return cache.get(key, default)
    except Exception:
        return default


def _safe_cache_set(key, value, timeout=None):
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        pass


def _atomic_write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _read_json(path: Path, default=None):
    try:
        with path.open('r', encoding='utf-8') as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else (default or {})
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return default or {}


def _validate_profile(name: str, value: dict) -> dict:
    if not isinstance(name, str) or not name or not isinstance(value, dict):
        raise ValueError('Invalid profile payload.')
    result = {}
    if 'widths' in value:
        widths = sorted({int(w) for w in value['widths'] if 16 <= int(w) <= 8192})
        if not widths:
            raise ValueError(f'Profile {name}: widths cannot be empty.')
        result['widths'] = widths
    if 'formats' in value:
        formats = [str(fmt).lower() for fmt in value['formats']]
        if not formats or any(fmt not in _ALLOWED_FORMATS for fmt in formats):
            raise ValueError(f'Profile {name}: invalid formats.')
        result['formats'] = formats
    if 'fallback_format' in value:
        fallback = str(value['fallback_format']).lower()
        if fallback not in _ALLOWED_FORMATS:
            raise ValueError(f'Profile {name}: invalid fallback format.')
        result['fallback_format'] = fallback
    if 'fit' in value:
        fit = str(value['fit']).lower()
        if fit not in _ALLOWED_FITS:
            raise ValueError(f'Profile {name}: invalid fit.')
        result['fit'] = fit
    if 'aspect_ratio' in value:
        ratio = value['aspect_ratio']
        if not isinstance(ratio, (list, tuple)) or len(ratio) != 2:
            raise ValueError(f'Profile {name}: invalid aspect_ratio.')
        result['aspect_ratio'] = [max(1, int(ratio[0])), max(1, int(ratio[1]))]
    for mapping_name in ('quality', 'target_bytes'):
        if mapping_name in value:
            mapping = value[mapping_name]
            if not isinstance(mapping, dict):
                raise ValueError(f'Profile {name}: {mapping_name} must be an object.')
            cleaned = {}
            for key, item in mapping.items():
                cleaned[str(key)] = int(item)
            result[mapping_name] = cleaned
    return result


def validate_remote_config(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError('Control-plane payload must be an object.')
    version = int(payload.get('version', 0))
    if version < 1:
        raise ValueError('Control-plane config version must be >= 1.')

    result = {
        'version': version,
        'updated_at': payload.get('updated_at'),
        'profiles': {},
        'feature_flags': {},
    }
    profiles = payload.get('profiles', {})
    if profiles:
        if not isinstance(profiles, dict):
            raise ValueError('profiles must be an object.')
        result['profiles'] = {name: _validate_profile(name, value) for name, value in profiles.items()}

    flags = payload.get('feature_flags', {})
    if flags:
        if not isinstance(flags, dict):
            raise ValueError('feature_flags must be an object.')
        allowed = {'auto_focal'}
        result['feature_flags'] = {key: bool(value) for key, value in flags.items() if key in allowed}

    # Security-critical settings such as storage credentials, API keys, DB/Redis,
    # and hostnames are deliberately NOT accepted from the control plane.
    return result


def load_last_known_good() -> dict:
    cached = _safe_cache_get(CONFIG_CACHE_KEY)
    if isinstance(cached, dict):
        return cached
    value = _read_json(_path('current.json'), default={})
    _safe_cache_set(CONFIG_CACHE_KEY, value, timeout=60)
    return value


def load_previous_config() -> dict:
    return _read_json(_path('previous.json'), default={})


def control_plane_status() -> dict:
    cached = _safe_cache_get(STATUS_CACHE_KEY)
    if isinstance(cached, dict):
        return cached
    return _read_json(_path('status.json'), default={'state': 'unknown'})


def _set_status(payload: dict):
    payload = dict(payload)
    payload['node_id'] = get_node_identity().node_id
    payload['recorded_at_epoch'] = int(time.time())
    _safe_cache_set(STATUS_CACHE_KEY, payload, timeout=None)
    try:
        _atomic_write_json(_path('status.json'), payload)
    except OSError:
        pass


def _circuit_open() -> bool:
    until = _safe_cache_get(CIRCUIT_CACHE_KEY, 0) or 0
    if not until:
        status = _read_json(_path('status.json'), default={})
        until = status.get('circuit_open_until_epoch', 0) or 0
    return float(until) > time.time()


def _open_circuit(error: str):
    seconds = int(getattr(settings, 'MEDIA_ENGINE_CONTROL_PLANE_CIRCUIT_SECONDS', 300))
    until = int(time.time()) + max(10, seconds)
    _safe_cache_set(CIRCUIT_CACHE_KEY, until, timeout=seconds)
    _set_status({
        'state': 'degraded',
        'last_error': error[:1000],
        'circuit_open_until_epoch': until,
        'last_known_good_version': load_last_known_good().get('version'),
    })


def sync_from_control_plane(force=False) -> dict:
    if not getattr(settings, 'MEDIA_ENGINE_CONTROL_PLANE_ENABLED', False):
        result = {'state': 'disabled', 'changed': False}
        _set_status(result)
        return result
    if _circuit_open() and not force:
        return {'state': 'circuit_open', 'changed': False, 'using_last_known_good': True}

    base_url = getattr(settings, 'MEDIA_ENGINE_CONTROL_PLANE_URL', '').rstrip('/')
    if not base_url:
        result = {'state': 'disabled', 'changed': False, 'reason': 'missing_url'}
        _set_status(result)
        return result

    identity = get_node_identity()
    query = urllib.parse.urlencode({
        'node_id': identity.node_id,
        'project_slug': identity.project_slug,
        'tenant_slug': identity.tenant_slug,
        'deployment_id': identity.deployment_id,
    })
    url = f'{base_url}/api/v1/media-engine/config/?{query}'
    headers = {
        'Accept': 'application/json',
        'User-Agent': f'MediaOptimizationEngine/{getattr(settings, "MEDIA_ENGINE_VERSION", "1.3.0")}',
    }
    token = getattr(settings, 'MEDIA_ENGINE_CONTROL_PLANE_TOKEN', '')
    if token:
        headers['Authorization'] = f'Bearer {token}'

    request = urllib.request.Request(url, headers=headers, method='GET')
    timeout = float(getattr(settings, 'MEDIA_ENGINE_CONTROL_PLANE_TIMEOUT_SECONDS', 3))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f'HTTP {response.status}')
            remote = json.loads(response.read().decode('utf-8'))
        validated = validate_remote_config(remote)
        current = load_last_known_good()
        changed = current != validated
        if changed:
            if current:
                _atomic_write_json(_path('previous.json'), current)
            _atomic_write_json(_path('current.json'), validated)
            _safe_cache_set(CONFIG_CACHE_KEY, validated, timeout=None)
        result = {
            'state': 'healthy',
            'changed': changed,
            'version': validated['version'],
            'using_last_known_good': True,
            'last_error': '',
            'circuit_open_until_epoch': 0,
        }
        _safe_cache_set(CIRCUIT_CACHE_KEY, 0, timeout=1)
        _set_status(result)
        return result
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
        _open_circuit(str(exc))
        return {
            'state': 'degraded',
            'changed': False,
            'using_last_known_good': True,
            'last_error': str(exc),
            'last_known_good_version': load_last_known_good().get('version'),
        }


def rollback_to_previous() -> dict:
    previous = load_previous_config()
    if not previous:
        raise RuntimeError('No previous control-plane configuration exists.')
    current = load_last_known_good()
    if current:
        _atomic_write_json(_path('rollback-source.json'), current)
    _atomic_write_json(_path('current.json'), previous)
    _safe_cache_set(CONFIG_CACHE_KEY, previous, timeout=None)
    _set_status({'state': 'rolled_back', 'version': previous.get('version'), 'changed': True})
    return previous
