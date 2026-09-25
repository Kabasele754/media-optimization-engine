"""Integration diagnostics for Media Optimization Engine.

Can be used either as a Django management command or directly with:
    python -m media_engine.doctor
"""
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    level: str = "ERROR"


def _yesno(value: bool) -> str:
    return "OK" if value else "FAIL"


def _package_checks() -> list[Check]:
    checks: list[Check] = []
    try:
        import media_engine
        checks.append(Check("package", True, f"media_engine {getattr(media_engine, '__version__', 'unknown')}"))
    except Exception as exc:
        return [Check("package", False, str(exc))]

    for module, label in [
        ("PIL", "Pillow"),
        ("PIL.AvifImagePlugin", "AVIF plugin"),
        ("rest_framework", "Django REST Framework"),
    ]:
        found = importlib.util.find_spec(module) is not None
        checks.append(Check(label, found, "installed" if found else "missing"))
    return checks


def run_diagnostics() -> list[Check]:
    checks = _package_checks()
    try:
        from django.conf import settings
        from django.apps import apps
        from django.core.cache import cache
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
    except Exception as exc:
        checks.append(Check("django runtime", False, f"Django unavailable: {exc}"))
        return checks

    if not settings.configured:
        checks.append(Check(
            "django settings",
            False,
            "settings are not configured; set DJANGO_SETTINGS_MODULE or run through manage.py",
        ))
        return checks

    installed = "media_engine" in settings.INSTALLED_APPS or any(
        str(item).startswith("media_engine.") for item in settings.INSTALLED_APPS
    )
    checks.append(Check(
        "INSTALLED_APPS",
        installed,
        "media_engine registered" if installed else 'add "media_engine" to INSTALLED_APPS',
    ))
    if not installed:
        return checks

    checks.append(Check("app registry", apps.is_installed("media_engine"), "Django app loaded"))

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks.append(Check("database", True, connection.vendor))
    except Exception as exc:
        checks.append(Check("database", False, str(exc)))

    try:
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes("media_engine")
        plan = executor.migration_plan(targets)
        pending = [f"{m.app_label}.{m.name}" for m, backwards in plan if not backwards and m.app_label == "media_engine"]
        checks.append(Check(
            "migrations",
            not pending,
            "all applied" if not pending else "pending: " + ", ".join(pending),
        ))
    except Exception as exc:
        checks.append(Check("migrations", False, str(exc)))

    try:
        key = "media_engine:doctor"
        cache.set(key, "ok", timeout=10)
        value = cache.get(key)
        checks.append(Check("cache", value == "ok", settings.CACHES.get("default", {}).get("BACKEND", "unknown")))
        cache.delete(key)
    except Exception as exc:
        checks.append(Check("cache", False, str(exc), level="WARN"))

    try:
        test_name = "media_engine/doctor/.write-test"
        saved = default_storage.save(test_name, ContentFile(b"media-engine-doctor"))
        exists = default_storage.exists(saved)
        if exists:
            default_storage.delete(saved)
        checks.append(Check("storage", exists, f"writable via {default_storage.__class__.__name__}"))
    except Exception as exc:
        checks.append(Check("storage", False, str(exc)))

    from .queueing import resolved_task_mode
    configured_mode = getattr(settings, "MEDIA_ENGINE_TASK_MODE", "auto")
    effective_mode = resolved_task_mode()
    checks.append(Check("task mode", True, f"configured={configured_mode}; effective={effective_mode}"))

    auto_fields = getattr(settings, "MEDIA_ENGINE_AUTO_FIELDS", {}) or {}
    auto_discover = bool(getattr(settings, "MEDIA_ENGINE_AUTO_DISCOVER_IMAGE_FIELDS", False))
    checks.append(Check("auto integration", True, f"configured_models={len(auto_fields)}; discover={auto_discover}"))

    try:
        from .processors.panorama.equirectangular import Panorama360Processor
        checks.append(Check("panorama processor", True, Panorama360Processor.__name__))
    except Exception as exc:
        checks.append(Check("panorama processor", False, str(exc)))

    try:
        from PIL import features
        checks.append(Check("WebP codec", bool(features.check("webp")), "Pillow WebP support"))
    except Exception as exc:
        checks.append(Check("WebP codec", False, str(exc), level="WARN"))

    return checks


def format_report(checks: Iterable[Check]) -> str:
    rows = ["Media Optimization Engine doctor", "=" * 32]
    failures = 0
    warnings = 0
    for c in checks:
        status = _yesno(c.ok)
        if not c.ok and c.level == "WARN":
            status = "WARN"
            warnings += 1
        elif not c.ok:
            failures += 1
        rows.append(f"[{status:4}] {c.name}: {c.detail}")
    rows.append("-" * 32)
    rows.append(f"Result: {failures} error(s), {warnings} warning(s)")
    return "\n".join(rows)


def main() -> int:
    settings_module = os.getenv("DJANGO_SETTINGS_MODULE")
    if settings_module:
        try:
            import django
            django.setup()
        except Exception as exc:
            print(f"Unable to initialize Django: {exc}", file=sys.stderr)
            return 2
    checks = run_diagnostics()
    print(format_report(checks))
    return 0 if all(c.ok or c.level == "WARN" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
