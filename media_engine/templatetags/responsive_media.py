from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from media_engine.manifest import build_manifest

register = template.Library()


def _srcset(items):
    return ', '.join(f"{escape(item['url'])} {item['width']}w" for item in items)


def _attrs(**values):
    parts = []
    for name, value in values.items():
        if value in (None, ''):
            continue
        html_name = 'class' if name == 'css_class' else name.rstrip('_').replace('_', '-')
        parts.append(f'{html_name}="{escape(value)}"')
    return (' ' + ' '.join(parts)) if parts else ''


def _merge_style(dominant_color, style):
    parts = []
    if dominant_color:
        parts.append(f'background:{dominant_color}')
    if style:
        parts.append(str(style).strip().rstrip(';'))
    return ';'.join(part for part in parts if part)


@register.simple_tag
def responsive_image(
    asset,
    profile='default',
    role='content',
    alt='',
    css_class='',
    sizes='100vw',
    picture_class='',
    picture_style='',
    width='',
    height='',
    loading='',
    decoding='async',
    fetchpriority='',
    style='',
    element_id='',
):
    """Render responsive sources while keeping presentation attributes on ``img``.

    ``picture_class`` / ``picture_style`` belong to the wrapper. Existing image CSS
    must continue to be passed as ``css_class`` (and optional ``style``), because the
    nested ``img`` remains the replaced element that owns geometry and object-fit.
    """
    manifest = build_manifest(asset, profile=profile)
    variants = manifest.get('variants', {})
    fallback = manifest.get('fallback')
    if not fallback:
        original = manifest.get('original_url')
        if not original:
            return ''
        fallback = {'url': original, 'width': manifest['width'], 'height': manifest['height']}

    eager = role == 'hero'
    resolved_loading = loading or ('eager' if eager else 'lazy')
    priority = fetchpriority or ('high' if eager else 'auto')
    source_parts = []
    if variants.get('avif'):
        source_parts.append(
            f'<source type="image/avif" srcset="{_srcset(variants["avif"])}" sizes="{escape(sizes)}">'
        )
    if variants.get('webp'):
        source_parts.append(
            f'<source type="image/webp" srcset="{_srcset(variants["webp"])}" sizes="{escape(sizes)}">'
        )

    resolved_width = width or fallback.get('width') or manifest['width']
    resolved_height = height or fallback.get('height') or manifest['height']
    merged_style = _merge_style(manifest.get('dominant_color'), style)
    img_attrs = _attrs(
        src=fallback['url'],
        alt=alt,
        css_class=css_class,
        width=str(resolved_width),
        height=str(resolved_height),
        loading=resolved_loading,
        decoding=decoding or 'async',
        fetchpriority=priority,
        style=merged_style,
        id=element_id,
    )
    picture_attrs = _attrs(css_class=picture_class, style=picture_style)
    return mark_safe(
        f'<picture{picture_attrs}>' + ''.join(source_parts) + f'<img{img_attrs}></picture>'
    )
