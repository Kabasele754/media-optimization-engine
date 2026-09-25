from django.test import SimpleTestCase
from PIL import Image
from media_engine.image_ops import resized, dominant_color


class ImageOpsTests(SimpleTestCase):
    def test_resize_preserves_aspect_ratio(self):
        image = Image.new('RGB', (1000, 500), 'red')
        out = resized(image, 500)
        self.assertEqual(out.size, (500, 250))

    def test_dominant_color(self):
        image = Image.new('RGB', (10, 10), (255, 0, 0))
        self.assertEqual(dominant_color(image), '#ff0000')
