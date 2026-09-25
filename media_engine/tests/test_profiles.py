from django.test import SimpleTestCase, override_settings
from media_engine.profiles import requested_widths


class ProfileTests(SimpleTestCase):
    def test_does_not_upscale(self):
        profile = {'widths': [320, 640, 1280]}
        self.assertEqual(requested_widths(profile, 800), [320, 640])
