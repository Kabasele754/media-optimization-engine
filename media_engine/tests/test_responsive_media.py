from unittest.mock import patch

from django.test import SimpleTestCase

from media_engine.templatetags.responsive_media import responsive_image


class ResponsiveImageTagTests(SimpleTestCase):
    def manifest(self):
        return {
            'width': 1600,
            'height': 900,
            'dominant_color': '#123456',
            'original_url': '/media/original.png',
            'fallback': {'url': '/media/fallback.webp', 'width': 1280, 'height': 720},
            'variants': {
                'avif': [{'url': '/media/640.avif', 'width': 640}],
                'webp': [{'url': '/media/640.webp', 'width': 640}],
            },
        }

    @patch('media_engine.templatetags.responsive_media.build_manifest')
    def test_keeps_image_presentation_attributes_on_nested_img(self, build_manifest):
        build_manifest.return_value = self.manifest()

        html = str(
            responsive_image(
                object(),
                css_class='tenant-logo rounded',
                picture_class='tenant-logo media-picture',
                style='object-fit:contain;width:100%',
                element_id='brand-logo',
                sizes='(max-width: 600px) 50vw, 240px',
            )
        )

        self.assertIn('<picture class="tenant-logo media-picture">', html)
        self.assertIn('class="tenant-logo rounded"', html)
        self.assertIn('id="brand-logo"', html)
        self.assertIn('style="background:#123456;object-fit:contain;width:100%"', html)
        self.assertIn('srcset="/media/640.avif 640w"', html)
        self.assertIn('srcset="/media/640.webp 640w"', html)
        self.assertIn('src="/media/fallback.webp"', html)

    @patch('media_engine.templatetags.responsive_media.build_manifest')
    def test_custom_loading_and_dimensions_override_defaults(self, build_manifest):
        build_manifest.return_value = self.manifest()

        html = str(
            responsive_image(
                object(),
                role='hero',
                width='320',
                height='180',
                loading='lazy',
                decoding='sync',
                fetchpriority='low',
            )
        )

        self.assertIn('width="320"', html)
        self.assertIn('height="180"', html)
        self.assertIn('loading="lazy"', html)
        self.assertIn('decoding="sync"', html)
        self.assertIn('fetchpriority="low"', html)

    @patch('media_engine.templatetags.responsive_media.build_manifest')
    def test_existing_call_signature_remains_compatible(self, build_manifest):
        build_manifest.return_value = self.manifest()

        html = str(responsive_image(object(), profile='card', role='content', alt='Card'))

        self.assertTrue(html.startswith('<picture>'))
        self.assertIn('alt="Card"', html)
        self.assertIn('loading="lazy"', html)
        self.assertIn('width="1280"', html)
        self.assertIn('height="720"', html)
