from __future__ import annotations

from ..base import ProcessorResult


class StandardAudioProcessor:
    name = "standard_audio"

    def supports(self, asset, profile_name: str) -> bool:
        return (
            getattr(asset, "media_kind", "") == "audio"
            or profile_name.startswith("audio.")
        )

    def process(self, asset, profile_name: str, force: bool = False) -> ProcessorResult:
        from ...services import generate_audio_variant

        generate_audio_variant(asset, profile_name=profile_name, force=force)
        return ProcessorResult(str(asset.pk), self.name, asset.status)
