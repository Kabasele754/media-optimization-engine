from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.files.base import File
from .models import MediaBinding
from .services import ingest_uploaded_file


def ingest_model_field(instance, *, field_name, profile='default', role='content'):
    field_file = getattr(instance, field_name, None)
    if not field_file or not getattr(field_file, 'name', None):
        return None
    with field_file.storage.open(field_file.name, 'rb') as source:
        wrapped = File(source, name=field_file.name.rsplit('/', 1)[-1])
        asset, created = ingest_uploaded_file(
            wrapped,
            owner_ref=f'{instance._meta.label}:{instance.pk}:{field_name}',
            profile=profile,
            enqueue=False,
        )
    ct = ContentType.objects.get_for_model(instance, for_concrete_model=False)
    previous = MediaBinding.objects.filter(
        content_type=ct, object_id=str(instance.pk), field_name=field_name
    ).select_related('asset').first()
    unchanged = previous is not None and previous.asset_id == asset.id and previous.profile == profile
    binding, _ = MediaBinding.objects.update_or_create(
        content_type=ct,
        object_id=str(instance.pk),
        field_name=field_name,
        defaults={'profile': profile, 'role': role, 'asset': asset},
    )
    if created or not unchanged:
        from .queueing import enqueue_asset
        transaction.on_commit(lambda: enqueue_asset(asset.id, profile=profile))
    return binding
