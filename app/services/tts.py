from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import AppSettings


@dataclass(slots=True)
class TTSArtifact:
    provider: str
    path: Path


class TTSProvider(Protocol):
    def synthesize(self, text: str, output_dir: Path, artifact_name: str) -> TTSArtifact | None:
        ...


class DisabledTTSProvider:
    def synthesize(self, text: str, output_dir: Path, artifact_name: str) -> TTSArtifact | None:
        output_dir.mkdir(parents=True, exist_ok=True)
        return None


class PlaceholderTTSProvider:
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def synthesize(self, text: str, output_dir: Path, artifact_name: str) -> TTSArtifact | None:
        raise NotImplementedError(f"TTS provider '{self.provider_name}' ainda nao foi implementado")


def build_tts_provider(settings: AppSettings) -> TTSProvider:
    if not settings.tts.enabled or settings.tts.provider.lower() == "disabled":
        return DisabledTTSProvider()
    return PlaceholderTTSProvider(settings.tts.provider)
