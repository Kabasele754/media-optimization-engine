from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.html import escape
from django.utils.safestring import mark_safe

from media_engine.manifest import build_manifest
from media_engine.models import MediaBinding

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


def _binding_for(instance, field_name):
    if instance is None or not getattr(instance, 'pk', None):
        return None
    content_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)
    return (
        MediaBinding.objects.filter(
            content_type=content_type,
            object_id=str(instance.pk),
            field_name=field_name,
        )
        .select_related('asset')
        .first()
    )


def _field_url(instance, field_name):
    field_file = getattr(instance, field_name, None) if instance is not None else None
    if not field_file:
        return ''
    try:
        return field_file.url
    except (AttributeError, ValueError):
        return ''


def _fallback_img(
    url,
    *,
    alt='',
    css_class='',
    width='',
    height='',
    loading='lazy',
    decoding='async',
    fetchpriority='auto',
    style='',
    element_id='',
):
    if not url:
        return ''
    attrs = _attrs(
        src=url,
        alt=alt,
        css_class=css_class,
        width=width,
        height=height,
        loading=loading,
        decoding=decoding,
        fetchpriority=fetchpriority,
        style=style,
        id=element_id,
    )
    return mark_safe(f'<img{attrs}>')


def _pick_variant(manifest, preferred_width=960, preferred_format='webp'):
    variants = manifest.get('variants', {})
    try:
        target_width = max(1, int(preferred_width))
    except (TypeError, ValueError):
        target_width = 960

    formats = []
    for fmt in (preferred_format, 'webp', 'avif'):
        if fmt and fmt not in formats:
            formats.append(fmt)

    for fmt in formats:
        candidates = list(variants.get(fmt) or [])
        if not candidates:
            continue
        candidates.sort(key=lambda item: int(item.get('width') or 0))
        for item in candidates:
            if int(item.get('width') or 0) >= target_width:
                return item
        return candidates[-1]

    return manifest.get('fallback') or None


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
    """Render responsive sources while keeping presentation attributes on the img."""
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


@register.simple_tag
def media_image(
    instance,
    field_name,
    profile='',
    role='',
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
    """Render a model ImageField or FileField through its MediaBinding."""
    binding = _binding_for(instance, field_name)
    resolved_role = role or (binding.role if binding else 'content')
    if binding:
        return responsive_image(
            binding.asset,
            profile=profile or binding.profile,
            role=resolved_role,
            alt=alt,
            css_class=css_class,
            sizes=sizes,
            picture_class=picture_class,
            picture_style=picture_style,
            width=width,
            height=height,
            loading=loading,
            decoding=decoding,
            fetchpriority=fetchpriority,
            style=style,
            element_id=element_id,
        )

    return _fallback_img(
        _field_url(instance, field_name),
        alt=alt,
        css_class=css_class,
        width=width,
        height=height,
        loading=loading or ('eager' if resolved_role == 'hero' else 'lazy'),
        decoding=decoding or 'async',
        fetchpriority=fetchpriority or ('high' if resolved_role == 'hero' else 'auto'),
        style=style,
        element_id=element_id,
    )


@register.simple_tag
def media_url(
    instance,
    field_name,
    preferred_width=960,
    preferred_format='webp',
    profile='',
):
    """Return one optimized derivative URL for CSS, metadata, email, or APIs."""
    binding = _binding_for(instance, field_name)
    if not binding:
        return _field_url(instance, field_name)

    manifest = build_manifest(binding.asset, profile=profile or binding.profile)
    variant = _pick_variant(
        manifest,
        preferred_width=preferred_width,
        preferred_format=preferred_format,
    )
    if variant and variant.get('url'):
        return variant['url']
    return manifest.get('original_url') or _field_url(instance, field_name)
