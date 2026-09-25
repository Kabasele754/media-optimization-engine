from __future__ import annotations

from .image.standard import StandardImageProcessor
from .panorama.equirectangular import Panorama360Processor

_PROCESSORS = [Panorama360Processor(), StandardImageProcessor()]


def get_processor(asset, profile_name: str):
    for processor in _PROCESSORS:
        if processor.supports(asset, profile_name):
            return processor
    raise RuntimeError(f'No media processor supports asset={asset.pk} profile={profile_name}')


def registered_processors():
    return tuple(p.name for p in _PROCESSORS)
