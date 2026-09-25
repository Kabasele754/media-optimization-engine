"""Portable automatic Django ImageField integration.

The package never has to know the host project's models at build time.
A project may explicitly list fields in ``MEDIA_ENGINE_AUTO_FIELDS`` or enable
opt-in ImageField discovery. Registered fields are connected to the normal MOE
post-save pipeline and therefore follow the host's task mode:

* local DEBUG / task mode ``auto`` -> inline (eager)
* production -> Celery
"""
from __future__ import annotations

import logging
from collections.abc import Mapping

from django.apps import apps
from django.conf import settings
from django.db.models import ImageField

from .registry import register_model_image

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDED_APPS = {
    "admin",
    "auth",
    "contenttypes",
    "sessions",
    "messages",
    "staticfiles",
    "media_engine",
}


def _field_profile(field_name: str) -> tuple[str, str]:
    name = field_name.lower()
    if "360" in name or "panorama" in name:
        return "panorama.multires", "panorama"
    if any(token in name for token in ("avatar", "profile", "logo", "icon")):
        return "avatar", "content"
    if any(token in name for token in ("hero", "cover", "banner")):
        return "hero", "hero"
    return "default", "content"


def _register_explicit_config() -> int:
    configured = getattr(settings, "MEDIA_ENGINE_AUTO_FIELDS", {}) or {}
    if not isinstance(configured, Mapping):
        raise TypeError("MEDIA_ENGINE_AUTO_FIELDS must be a mapping")

    count = 0
    for model_label, fields in configured.items():
        model = apps.get_model(model_label)
        if model is None:
            logger.warning("MOE auto integration: unknown model %s", model_label)
            continue

        if isinstance(fields, (list, tuple, set)):
            fields = {name: {} for name in fields}
        if not isinstance(fields, Mapping):
            raise TypeError(f"MEDIA_ENGINE_AUTO_FIELDS[{model_label!r}] must be a mapping or list")

        for field_name, options in fields.items():
            options = options or {}
            if not isinstance(options, Mapping):
                raise TypeError(f"MOE options for {model_label}.{field_name} must be a mapping")
            inferred_profile, inferred_role = _field_profile(field_name)
            register_model_image(
                model,
                field_name,
                profile=str(options.get("profile") or inferred_profile),
                role=str(options.get("role") or inferred_role),
            )
            count += 1
    return count


def _register_discovered_fields() -> int:
    if not getattr(settings, "MEDIA_ENGINE_AUTO_DISCOVER_IMAGE_FIELDS", False):
        return 0

    excluded = set(getattr(settings, "MEDIA_ENGINE_AUTO_DISCOVER_EXCLUDE_APPS", ()) or ())
    excluded |= DEFAULT_EXCLUDED_APPS
    count = 0

    for model in apps.get_models():
        if model._meta.app_label in excluded:
            continue
        for field in model._meta.get_fields():
            if not isinstance(field, ImageField):
                continue
            profile, role = _field_profile(field.name)
            register_model_image(model, field.name, profile=profile, role=role)
            count += 1
    return count


def configure_auto_integration() -> dict[str, int]:
    """Register configured host fields once during Django app startup."""
    explicit = _register_explicit_config()
    discovered = _register_discovered_fields()
    if explicit or discovered:
        logger.info(
            "MOE automatic integration registered %s explicit and %s discovered ImageField(s)",
            explicit,
            discovered,
        )
    return {"explicit": explicit, "discovered": discovered}
