from django.apps import AppConfig


class MediaEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "media_engine"

    def ready(self):
        from . import signals  # noqa: F401
        from .autoregister import configure_auto_integration
        configure_auto_integration()
