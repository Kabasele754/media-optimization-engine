from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PanoramaDetection:
    is_panorama: bool
    projection: str
    confidence: str
    reason: str


def detect_equirectangular(width: int, height: int, metadata: dict | None = None) -> PanoramaDetection:
    metadata = metadata or {}
    projection_type = str(metadata.get('ProjectionType') or metadata.get('GPano:ProjectionType') or '').lower()
    if projection_type == 'equirectangular':
        return PanoramaDetection(True, 'equirectangular', 'high', 'GPano/XMP projection metadata')
    if height > 0:
        ratio = width / height
        if width >= 2048 and 1.98 <= ratio <= 2.02:
            return PanoramaDetection(True, 'equirectangular', 'medium', '2:1 dimensions typical of equirectangular panoramas')
    return PanoramaDetection(False, '', 'low', 'No reliable panorama signal')
