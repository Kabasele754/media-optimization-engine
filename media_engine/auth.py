import hmac
from django.conf import settings
from rest_framework.permissions import BasePermission


def configured_api_keys():
    value = getattr(settings, 'MEDIA_ENGINE_API_KEYS', '')
    if isinstance(value, (tuple, list, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(',') if item.strip()]


def extract_api_key(request):
    auth = request.headers.get('Authorization', '').strip()
    if auth.lower().startswith('bearer '):
        return auth.split(' ', 1)[1].strip()
    return request.headers.get('X-Media-Engine-Key', '').strip()


def valid_api_key(value):
    keys = configured_api_keys()
    if not keys:
        return False
    return any(hmac.compare_digest(value or '', key) for key in keys)


class MediaEngineApiKeyPermission(BasePermission):
    message = 'A valid Media Optimization Engine API key is required.'

    def has_permission(self, request, view):
        if not getattr(settings, 'MEDIA_ENGINE_REQUIRE_API_KEY', False):
            return True
        return valid_api_key(extract_api_key(request))
