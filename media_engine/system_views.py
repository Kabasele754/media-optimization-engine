import json
from importlib import resources
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from .control_plane import control_plane_status
from .health import build_health_report
from .node import get_node_identity
from .runtime_config import effective_profiles


def _version():
    return getattr(settings, 'MEDIA_ENGINE_VERSION', '1.4.0')


@require_GET
def well_known(request):
    identity = get_node_identity()
    return JsonResponse({
        'service': 'Media Optimization Engine',
        'version': _version(),
        'api_version': 'v1',
        'node': identity.as_dict(),
        'autonomy': {
            'runtime_requires_control_plane': False,
            'last_known_good_config': True,
            'panorama_multires': True,
            'panorama_cubemap': True,
            'viewer_adapters': ['generic', 'pannellum', 'marzipano', 'threejs', 'flutter'],
            'local_processing': True,
            'local_storage_supported': True,
            'object_storage_supported': True,
        },
        'discovery': {
            'base_api': '/api/v1/',
            'capabilities': '/api/v1/system/capabilities/',
            'health': '/api/v1/system/health/',
            'openapi': '/api/v1/system/openapi.yaml',
            'version': '/api/v1/system/version/',
        },
        'authentication': {
            'type': 'bearer_api_key',
            'header': 'Authorization: Bearer <key>',
            'required': bool(getattr(settings, 'MEDIA_ENGINE_REQUIRE_API_KEY', False)),
        },
    })


@require_GET
def capabilities(request):
    return JsonResponse({
        'service': 'Media Optimization Engine',
        'version': _version(),
        'node': get_node_identity().as_dict(),
        'formats': ['avif', 'webp', 'jpeg'],
        'profiles': effective_profiles(),
        'features': {
            'content_addressed_storage': True,
            'deduplication': bool(getattr(settings, 'MEDIA_ENGINE_DEDUPLICATE', True)),
            'async_generation': True,
            'smart_quality_budget': True,
            'focal_point': True,
            'automatic_focal_point': bool(getattr(settings, 'MEDIA_ENGINE_AUTO_FOCAL', False)),
            'blurhash': True,
            'dominant_color': True,
            'cdn_ready': True,
            's3_r2_minio_ready': True,
            'offline_from_control_plane': True,
            'last_known_good_config': True,
            'panorama_multires': True,
            'panorama_cubemap': True,
            'viewer_adapters': ['generic', 'pannellum', 'marzipano', 'threejs', 'flutter'],
        },
        'control_plane': control_plane_status(),
    })


@require_GET
def version(request):
    return JsonResponse({
        'service': 'Media Optimization Engine',
        'version': _version(),
        'pipeline_version': getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1),
        'node': get_node_identity().as_dict(),
    })


@require_GET
def health(request):
    deep = request.GET.get('deep', '').lower() in {'1', 'true', 'yes'}
    report = build_health_report(deep=deep)
    status = 503 if report['state'] == 'unhealthy' else 200
    return JsonResponse(report, status=status)


@require_GET
def openapi_yaml(request):
    spec = resources.files('media_engine').joinpath('spec/openapi.yaml').read_text(encoding='utf-8')
    return HttpResponse(spec, content_type='application/yaml; charset=utf-8')
