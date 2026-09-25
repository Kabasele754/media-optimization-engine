from dataclasses import dataclass
from django.db import transaction
from django.db.models.signals import post_save

_REGISTRY = []
_REGISTRY_KEYS = set()


@dataclass
class RegistryEntry:
    model: object
    field_name: str
    profile: str
    role: str


def register_model_image(model, field_name, profile='default', role='content'):
    key = (model._meta.label_lower, field_name)
    if key in _REGISTRY_KEYS:
        return next(entry for entry in _REGISTRY if (entry.model._meta.label_lower, entry.field_name) == key)

    model._meta.get_field(field_name)
    entry = RegistryEntry(model=model, field_name=field_name, profile=profile, role=role)
    _REGISTRY.append(entry)
    _REGISTRY_KEYS.add(key)

    def handler(sender, instance, created=False, raw=False, update_fields=None, **kwargs):
        if raw:
            return
        if update_fields is not None and field_name not in update_fields:
            return

        def _ingest():
            from .integration import ingest_model_field
            ingest_model_field(instance, field_name=field_name, profile=profile, role=role)

        transaction.on_commit(_ingest)

    post_save.connect(
        handler,
        sender=model,
        weak=False,
        dispatch_uid=f'media-engine:{model._meta.label_lower}:{field_name}',
    )
    return entry


def entries():
    return list(_REGISTRY)
