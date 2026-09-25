from copy import deepcopy
from django.conf import settings
from .control_plane import load_last_known_good


def _merge_profile(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if key in {'quality', 'target_bytes'} and isinstance(value, dict):
            merged = dict(result.get(key, {}))
            for subkey, subvalue in value.items():
                if key == 'target_bytes':
                    try:
                        subkey = int(subkey)
                    except (TypeError, ValueError):
                        pass
                merged[subkey] = subvalue
            result[key] = merged
        else:
            result[key] = value
    return result


def effective_profiles() -> dict:
    profiles = deepcopy(getattr(settings, 'MEDIA_ENGINE_PROFILES', {}))
    snapshot = load_last_known_good()
    for name, override in snapshot.get('profiles', {}).items():
        if name in profiles:
            profiles[name] = _merge_profile(profiles[name], override)
        else:
            profiles[name] = deepcopy(override)
    return profiles


def effective_feature_flags() -> dict:
    snapshot = load_last_known_good()
    return dict(snapshot.get('feature_flags', {}))
