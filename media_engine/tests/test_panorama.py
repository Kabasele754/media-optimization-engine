from django.test import SimpleTestCase
from PIL import Image

from media_engine.processors.panorama.detect import detect_equirectangular
from media_engine.processors.panorama.tiles import pyramid_widths, build_plan
from media_engine.processors.panorama.cubemap import equirectangular_to_cubemap


class PanoramaMathTests(SimpleTestCase):
    def test_detects_typical_equirectangular_ratio(self):
        result = detect_equirectangular(8192, 4096)
        self.assertTrue(result.is_panorama)
        self.assertEqual(result.projection, 'equirectangular')

    def test_rejects_normal_landscape(self):
        result = detect_equirectangular(1600, 900)
        self.assertFalse(result.is_panorama)

    def test_pyramid_widths(self):
        self.assertEqual(pyramid_widths(8192, 1024), [1024, 2048, 4096, 8192])

    def test_tile_plan(self):
        plan = build_plan(2048, 512, 1)
        self.assertEqual((plan.cols, plan.rows), (4, 2))
        self.assertEqual((plan.width, plan.height), (2048, 1024))

    def test_cubemap_has_six_faces(self):
        image = Image.new('RGB', (512, 256), (120, 80, 40))
        faces = equirectangular_to_cubemap(image, 64)
        self.assertEqual(set(faces), {'front', 'back', 'left', 'right', 'top', 'bottom'})
        self.assertTrue(all(face.size == (64, 64) for face in faces.values()))
