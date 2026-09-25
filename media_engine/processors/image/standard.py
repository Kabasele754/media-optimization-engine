from __future__ import annotations

from ..base import ProcessorResult


class StandardImageProcessor:
    name = 'standard_image'

    def supports(self, asset, profile_name: str) -> bool:
        return getattr(asset, 'media_kind', 'image') == 'image' and not profile_name.startswith('panorama.')

    def process(self, asset, profile_name: str, force: bool = False) -> ProcessorResult:
        from ...services import generate_standard_variants

        generate_standard_variants(asset, profile_name=profile_name, force=force)
        return ProcessorResult(str(asset.pk), self.name, asset.status)
