from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("media-optimization-engine")
except PackageNotFoundError:
    __version__ = "0+unknown"


def register_model_image(*args, **kwargs):
    from .registry import register_model_image as _register
    return _register(*args, **kwargs)


default_app_config = "media_engine.apps.MediaEngineConfig"
