__version__ = '1.4.0rc3'

def register_model_image(*args, **kwargs):
    from .registry import register_model_image as _register
    return _register(*args, **kwargs)

default_app_config = 'media_engine.apps.MediaEngineConfig'
