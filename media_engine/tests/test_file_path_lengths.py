from django.test import SimpleTestCase

from media_engine.models import MediaAsset, MediaVariant, PanoramaTile


class MediaFilePathLengthTests(SimpleTestCase):
    def test_generated_media_file_fields_allow_long_storage_paths(self):
        self.assertGreaterEqual(
            MediaAsset._meta.get_field("original_file").max_length,
            500,
        )
        self.assertGreaterEqual(
            MediaAsset._meta.get_field("panorama_preview").max_length,
            500,
        )
        self.assertGreaterEqual(
            MediaVariant._meta.get_field("file").max_length,
            500,
        )
        self.assertGreaterEqual(
            PanoramaTile._meta.get_field("file").max_length,
            500,
        )

    def test_marzipano_tile_path_can_exceed_legacy_100_character_limit(self):
        sha = "a" * 64
        path = (
            f"media_engine/panoramas/{sha[:2]}/"
            f"{sha}/v1/panorama.marzipano/"
            "l3/f/12_15.webp"
        )
        self.assertGreater(len(path), 100)
        self.assertLessEqual(
            len(path),
            PanoramaTile._meta.get_field("file").max_length,
        )
