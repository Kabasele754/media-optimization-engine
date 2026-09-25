import hashlib
import io
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction, IntegrityError
from django.utils import timezone
from .image_ops import normalized_image, dominant_color, make_blurhash, placeholder_data_url, resized, encode_with_budget
from .metrics import IMAGES_INGESTED, ORIGINAL_BYTES, VARIANTS_GENERATED, VARIANT_FAILURES, GENERATION_SECONDS, DERIVATIVE_BYTES
from .models import MediaAsset, MediaVariant
from .profiles import get_profile, requested_widths, all_formats
from .storage_paths import safe_extension, original_storage_name, derivative_storage_name
from .validators import inspect_upload
from .locks import cache_lock
from .runtime_config import effective_feature_flags


def ingest_uploaded_file(uploaded_file, *, owner_ref='', focal_x=None, focal_y=None, profile='default', enqueue=True, media_kind='', projection=''):
    raw, fmt, mime, width, height = inspect_upload(uploaded_file)
    sha = hashlib.sha256(raw).hexdigest()
    extension = safe_extension(fmt)
    version = getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)

    existing = MediaAsset.objects.filter(original_sha256=sha).first()
    if existing and getattr(settings, 'MEDIA_ENGINE_DEDUPLICATE', True):
        if enqueue:
            from .queueing import enqueue_asset
            transaction.on_commit(lambda: enqueue_asset(existing.id, profile=profile))
        return existing, False

    storage_name = original_storage_name(sha, extension)
    if not default_storage.exists(storage_name):
        default_storage.save(storage_name, ContentFile(raw))

    image = normalized_image(io.BytesIO(raw))
    from .processors.panorama.detect import detect_equirectangular
    detection = detect_equirectangular(width, height, getattr(image, 'info', {}) or {})
    if not media_kind:
        media_kind = 'panorama' if (profile.startswith('panorama.') or detection.is_panorama) else 'image'
    if media_kind == 'panorama' and not projection:
        projection = detection.projection or 'equirectangular'
    feature_flags = effective_feature_flags()
    auto_focal = feature_flags.get('auto_focal', getattr(settings, 'MEDIA_ENGINE_AUTO_FOCAL', False))
    if auto_focal and focal_x is None and focal_y is None:
        from .focal_detectors import detect_focal_point
        auto_x, auto_y = detect_focal_point(image)
        focal_x = auto_x
        focal_y = auto_y
    try:
        asset = MediaAsset.objects.create(
            original_sha256=sha,
            original_file=storage_name,
            original_name=Path(getattr(uploaded_file, 'name', '')).name,
            mime_type=mime,
            width=width,
            height=height,
            original_size=len(raw),
            media_kind=media_kind,
            projection=projection,
            processor='panorama_360' if media_kind == 'panorama' else 'standard_image',
            metadata_json={
                'panorama_detection_confidence': detection.confidence,
                'panorama_detection_reason': detection.reason,
            },
            dominant_color=dominant_color(image),
            blurhash=make_blurhash(image),
            placeholder_data_url=placeholder_data_url(image),
            focal_x=focal_x,
            focal_y=focal_y,
            processor_version=version,
            owner_ref=owner_ref,
        )
        created = True
        IMAGES_INGESTED.inc()
        ORIGINAL_BYTES.inc(len(raw))
    except IntegrityError:
        asset = MediaAsset.objects.get(original_sha256=sha)
        created = False
    if enqueue:
        from .queueing import enqueue_asset
        transaction.on_commit(lambda: enqueue_asset(asset.id, profile=profile))
    return asset, created


def generate_variant(asset, *, profile_name, width, fmt, force=False):
    version = getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)
    profile = get_profile(profile_name)
    lock_key = f'media-engine:{asset.id}:{version}:{profile_name}:{width}:{fmt}'
    with cache_lock(lock_key) as acquired:
        if not acquired:
            return None
        existing = MediaVariant.objects.filter(
            asset=asset,
            profile=profile_name,
            width=width,
            format=fmt,
            processor_version=version,
            status=MediaVariant.Status.READY,
        ).first()
        if existing and not force:
            return existing

        variant, _ = MediaVariant.objects.get_or_create(
            asset=asset,
            profile=profile_name,
            width=width,
            format=fmt,
            processor_version=version,
            defaults={'height': 0, 'status': MediaVariant.Status.PROCESSING},
        )
        variant.status = MediaVariant.Status.PROCESSING
        variant.last_error = ''
        variant.save(update_fields=['status', 'last_error', 'updated_at'])

        try:
            with default_storage.open(asset.original_file.name, 'rb') as source:
                image = normalized_image(source)
            work = resized(
                image,
                width,
                fit=profile.get('fit', 'contain'),
                aspect_ratio=profile.get('aspect_ratio'),
                focal_x=asset.focal_x,
                focal_y=asset.focal_y,
            )
            quality = profile.get('quality', {}).get(fmt, 75)
            target = profile.get('target_bytes', {}).get(width)
            with GENERATION_SECONDS.labels(format=fmt, profile=profile_name).time():
                encoded = encode_with_budget(work, fmt, quality, target_bytes=target)
            path = derivative_storage_name(asset.original_sha256, version, profile_name, width, fmt)
            if default_storage.exists(path):
                default_storage.delete(path)
            stored = default_storage.save(path, ContentFile(encoded.content))
            variant.file = stored
            variant.height = encoded.height
            variant.file_size = len(encoded.content)
            variant.quality = encoded.quality
            variant.status = MediaVariant.Status.READY
            variant.last_error = ''
            variant.save()
            VARIANTS_GENERATED.labels(format=fmt, profile=profile_name).inc()
            DERIVATIVE_BYTES.labels(format=fmt).inc(len(encoded.content))
            return variant
        except Exception as exc:
            variant.status = MediaVariant.Status.FAILED
            variant.last_error = str(exc)
            variant.save(update_fields=['status', 'last_error', 'updated_at'])
            VARIANT_FAILURES.labels(format=fmt, profile=profile_name).inc()
            raise


def generate_standard_variants(asset, profile_name='default', force=False):
    profile = get_profile(profile_name)
    expected = []
    errors = []
    asset.status = MediaAsset.Status.PROCESSING
    asset.last_error = ''
    asset.save(update_fields=['status', 'last_error', 'updated_at'])
    for width in requested_widths(profile, asset.width):
        for fmt in all_formats(profile):
            expected.append((width, fmt))
            try:
                generate_variant(asset, profile_name=profile_name, width=width, fmt=fmt, force=force)
            except Exception as exc:
                errors.append(f'{width}.{fmt}: {exc}')

    ready_count = MediaVariant.objects.filter(
        asset=asset,
        profile=profile_name,
        processor_version=getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1),
        status=MediaVariant.Status.READY,
    ).count()
    asset.status = MediaAsset.Status.READY if ready_count >= len(expected) and not errors else (MediaAsset.Status.PARTIAL if ready_count else MediaAsset.Status.FAILED)
    asset.last_error = '\n'.join(errors[-20:])
    asset.processed_at = timezone.now()
    asset.processor_version = getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)
    asset.save(update_fields=['status', 'last_error', 'processed_at', 'processor_version', 'updated_at'])
    from .manifest import invalidate_manifest
    invalidate_manifest(asset.id)
    return asset


def generate_all_variants(asset, profile_name='default', force=False):
    from .processors.registry import get_processor
    processor = get_processor(asset, profile_name)
    return processor.process(asset, profile_name, force=force)
