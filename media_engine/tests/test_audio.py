from types import SimpleNamespace

from django.test import SimpleTestCase

from media_engine.audio_ops import AUDIO_EXTENSIONS
from media_engine.processors.audio.standard import StandardAudioProcessor
from media_engine.profiles import get_profile


class AudioProfileTests(SimpleTestCase):
    def test_invitation_audio_profile_is_compact_mp3(self):
        profile = get_profile("audio.invitation")
        self.assertEqual(profile["fallback_format"], "mp3")
        self.assertEqual(profile["bitrate_kbps"], 96)
        self.assertLessEqual(profile["max_duration_seconds"], 600)

    def test_standard_audio_processor_matches_audio_assets(self):
        processor = StandardAudioProcessor()
        asset = SimpleNamespace(media_kind="audio", pk="audio")
        self.assertTrue(processor.supports(asset, "audio.invitation"))
        self.assertFalse(processor.supports(SimpleNamespace(media_kind="image", pk="image"), "hero"))

    def test_expected_browser_audio_extensions_are_allowed(self):
        self.assertTrue({"mp3", "m4a", "wav", "ogg", "opus", "webm"}.issubset(AUDIO_EXTENSIONS))
