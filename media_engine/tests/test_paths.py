from django.test import SimpleTestCase
from media_engine.storage_paths import original_storage_name, derivative_storage_name


class StoragePathTests(SimpleTestCase):
    def test_paths_are_content_addressed(self):
        sha = 'ab' * 32
        self.assertIn('/ab/ab/', original_storage_name(sha, 'jpg'))
        self.assertIn('/v1/hero/640.avif', derivative_storage_name(sha, 1, 'hero', 640, 'avif'))
