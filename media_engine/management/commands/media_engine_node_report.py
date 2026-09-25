import json
from django.conf import settings
from django.core.management.base import BaseCommand
from media_engine.control_plane import control_plane_status, load_last_known_good
from media_engine.node import get_node_identity
from media_engine.runtime_config import effective_profiles


class Command(BaseCommand):
    help = 'Print node identity, autonomy configuration and active image profiles.'

    def handle(self, *args, **options):
        payload = {
            'version': getattr(settings, 'MEDIA_ENGINE_VERSION', '1.4.0'),
            'pipeline_version': getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1),
            'node': get_node_identity().as_dict(),
            'require_api_key': getattr(settings, 'MEDIA_ENGINE_REQUIRE_API_KEY', False),
            'control_plane_enabled': getattr(settings, 'MEDIA_ENGINE_CONTROL_PLANE_ENABLED', False),
            'control_plane_runtime_dependency': False,
            'control_plane_status': control_plane_status(),
            'last_known_good': load_last_known_good(),
            'profiles': effective_profiles(),
        }
        self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
