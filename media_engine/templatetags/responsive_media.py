from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from media_engine.manifest import build_manifest

register = template.Library()


def _srcset(items):
    return ', '.join(f"{escape(item['url'])} {item['width']}w" for item in items)


@register.simple_tag
def responsive_image(asset, profile='default', role='content', alt='', css_class='', sizes='100vw'):
    manifest = build_manifest(asset, profile=profile)
    variants = manifest.get('variants', {})
    fallback = manifest.get('fallback')
    if not fallback:
        original = manifest.get('original_url')
        if not original:
            return ''
        fallback = {'url': original, 'width': manifest['width'], 'height': manifest['height']}

    eager = role == 'hero'
    loading = 'eager' if eager else 'lazy'
    priority = 'high' if eager else 'auto'
    source_parts = []
    if variants.get('avif'):
        source_parts.append(f'<source type="image/avif" srcset="{_srcset(variants["avif"])}" sizes="{escape(sizes)}">')
    if variants.get('webp'):
        source_parts.append(f'<source type="image/webp" srcset="{_srcset(variants["webp"])}" sizes="{escape(sizes)}">')
    width = fallback.get('width') or manifest['width']
    height = fallback.get('height') or manifest['height']
    img = (
        f'<img src="{escape(fallback["url"])}" alt="{escape(alt)}" class="{escape(css_class)}" '
        f'width="{width}" height="{height}" loading="{loading}" decoding="async" '
        f'fetchpriority="{priority}" style="background:{escape(manifest.get("dominant_color") or "transparent")}">'
    )
    return mark_safe('<picture>' + ''.join(source_parts) + img + '</picture>')
