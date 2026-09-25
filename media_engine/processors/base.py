from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProcessorResult:
    asset_id: str
    processor: str
    status: str


class MediaProcessor(Protocol):
    name: str

    def supports(self, asset, profile_name: str) -> bool:
        ...

    def process(self, asset, profile_name: str, force: bool = False) -> ProcessorResult:
        ...
