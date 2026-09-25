import json
import tempfile
from pathlib import Path

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from media_engine.auth import MediaEngineApiKeyPermission
from media_engine.control_plane import CONFIG_CACHE_KEY, validate_remote_config
from media_engine.node import get_node_identity
from media_engine.runtime_config import effective_profiles


class DistributedNodeTests(SimpleTestCase):
    @override_settings(
        MEDIA_ENGINE_NODE_ID='node-a',
        MEDIA_ENGINE_PROJECT_SLUG='project-a',
        MEDIA_ENGINE_TENANT_SLUG='tenant-a',
        MEDIA_ENGINE_DEPLOYMENT_ID='prod-1',
    )
    def test_node_identity_is_local(self):
        identity = get_node_identity()
        self.assertEqual(identity.node_id, 'node-a')
        self.assertEqual(identity.project_slug, 'project-a')
        self.assertEqual(identity.tenant_slug, 'tenant-a')

    @override_settings(MEDIA_ENGINE_REQUIRE_API_KEY=True, MEDIA_ENGINE_API_KEYS='secret-a,secret-b')
    def test_api_key_permission(self):
        factory = APIRequestFactory()
        permission = MediaEngineApiKeyPermission()
        good = factory.get('/api/v1/images/', HTTP_AUTHORIZATION='Bearer secret-b')
        bad = factory.get('/api/v1/images/', HTTP_AUTHORIZATION='Bearer wrong')
        self.assertTrue(permission.has_permission(good, None))
        self.assertFalse(permission.has_permission(bad, None))

    def test_control_plane_rejects_secret_settings(self):
        validated = validate_remote_config({
            'version': 2,
            'profiles': {'hero': {'quality': {'avif': 55}}},
            'feature_flags': {'auto_focal': True, 'shell_command': True},
            'AWS_SECRET_ACCESS_KEY': 'must-not-pass',
            'REDIS_URL': 'must-not-pass',
        })
        self.assertNotIn('AWS_SECRET_ACCESS_KEY', validated)
        self.assertNotIn('REDIS_URL', validated)
        self.assertNotIn('shell_command', validated['feature_flags'])
        self.assertTrue(validated['feature_flags']['auto_focal'])

    def test_last_known_good_profile_override_is_local_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'current.json').write_text(json.dumps({
                'version': 3,
                'profiles': {'hero': {'quality': {'avif': 41}}},
                'feature_flags': {},
            }))
            cache.delete(CONFIG_CACHE_KEY)
            with override_settings(
                MEDIA_ENGINE_CONFIG_DIR=tmp,
                MEDIA_ENGINE_PROFILES={
                    'hero': {
                        'widths': [640, 1280],
                        'formats': ['avif', 'webp'],
                        'quality': {'avif': 58, 'webp': 78},
                    }
                },
            ):
                profiles = effective_profiles()
                self.assertEqual(profiles['hero']['quality']['avif'], 41)
                self.assertEqual(profiles['hero']['quality']['webp'], 78)
                self.assertEqual(profiles['hero']['widths'], [640, 1280])
            cache.delete(CONFIG_CACHE_KEY)
