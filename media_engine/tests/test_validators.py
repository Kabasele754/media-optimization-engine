from io import BytesIO
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from media_engine.validators import inspect_upload


class MpoValidationTests(SimpleTestCase):
    @patch("media_engine.validators.Image.open")
    def test_mpo_is_normalized_as_jpeg(self, image_open):
        image = MagicMock()
        image.format = "MPO"
        image.size = (1200, 800)
        image.verify.return_value = None
        image_open.return_value = image

        upload = SimpleUploadedFile(
            "portrait.jpg",
            b"fake-mpo-container",
            content_type="image/jpeg",
        )

        raw, fmt, mime, width, height = inspect_upload(upload)

        self.assertEqual(raw, b"fake-mpo-container")
        self.assertEqual(fmt, "JPEG")
        self.assertEqual(mime, "image/jpeg")
        self.assertEqual((width, height), (1200, 800))
