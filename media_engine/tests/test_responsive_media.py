from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from media_engine.templatetags.responsive_media import media_image, media_url, responsive_image


class ResponsiveImageTagTests(SimpleTestCase):
    def manifest(self):
        return {
            'width': 1600,
            'height': 900,
            'dominant_color': '#123456',
            'original_url': '/media/original.png',
            'fallback': {'url': '/media/fallback.webp', 'width': 1280, 'height': 720},
            'variants': {
                'avif': [
                    {'url': '/media/480.avif', 'width': 480, 'height': 270},
                    {'url': '/media/960.avif', 'width': 960, 'height': 540},
                ],
                'webp': [
                    {'url': '/media/480.webp', 'width': 480, 'height': 270},
                    {'url': '/media/960.webp', 'width': 960, 'height': 540},
                    {'url': '/media/1280.webp', 'width': 1280, 'height': 720},
                ],
            },
        }

    @patch('media_engine.templatetags.responsive_media.build_manifest')
    def test_keeps_image_presentation_attributes_on_nested_img(self, build_manifest):
        build_manifest.return_value = self.manifest()

        html = str(
            responsive_image(
                object(),
                css_class='site-logo rounded',
                picture_class='media-picture site-logo-wrap',
                style='object-fit:contain;width:100%',
                element_id='brand-logo',
                sizes='(max-width: 600px) 50vw, 240px',
            )
        )

        self.assertIn('<picture class="media-picture site-logo-wrap">', html)
        self.assertIn('class="site-logo rounded"', html)
        self.assertIn('id="brand-logo"', html)
        self.assertIn('style="background:#123456;object-fit:contain;width:100%"', html)
        self.assertIn('srcset="/media/480.avif 480w, /media/960.avif 960w"', html)
        self.assertIn('srcset="/media/480.webp 480w, /media/960.webp 960w, /media/1280.webp 1280w"', html)
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

    @patch('media_engine.templatetags.responsive_media._binding_for')
    @patch('media_engine.templatetags.responsive_media.build_manifest')
    def test_media_image_resolves_model_field_binding(self, build_manifest, binding_for):
        build_manifest.return_value = self.manifest()
        binding_for.return_value = SimpleNamespace(
            asset=object(),
            profile='hero',
            role='hero',
        )

        html = str(
            media_image(
                SimpleNamespace(pk=7),
                'cover_image',
                alt='Article cover',
                css_class='article-hero',
                sizes='(max-width: 768px) 100vw, 1200px',
            )
        )

        self.assertIn('<picture', html)
        self.assertIn('class="article-hero"', html)
        self.assertIn('loading="eager"', html)
        self.assertIn('fetchpriority="high"', html)
        self.assertIn('/media/960.avif 960w', html)

    @patch('media_engine.templatetags.responsive_media._field_url')
    @patch('media_engine.templatetags.responsive_media._binding_for')
    def test_media_image_falls_back_to_field_url_without_binding(self, binding_for, field_url):
        binding_for.return_value = None
        field_url.return_value = '/uploads/photo.jpg'

        html = str(
            media_image(
                SimpleNamespace(pk=9),
                'photo',
                alt='Profile',
                css_class='avatar',
            )
        )

        self.assertTrue(html.startswith('<img'))
        self.assertIn('src="/uploads/photo.jpg"', html)
        self.assertIn('loading="lazy"', html)

    @patch('media_engine.templatetags.responsive_media._binding_for')
    @patch('media_engine.templatetags.responsive_media.build_manifest')
    def test_media_url_selects_smallest_variant_at_or_above_target(self, build_manifest, binding_for):
        build_manifest.return_value = self.manifest()
        binding_for.return_value = SimpleNamespace(asset=object(), profile='default')

        url = media_url(
            SimpleNamespace(pk=3),
            'logo',
            preferred_width=700,
            preferred_format='webp',
        )

        self.assertEqual(url, '/media/960.webp')
