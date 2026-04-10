from __future__ import annotations

from dataclasses import dataclass
import importlib
import shutil
from pathlib import Path
import tempfile
from typing import Protocol
import wave

from app.core.config import AppSettings
from app.core.text_utils import chunk_text


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


class PiperTTSProvider:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.provider_name = "piper"
        self.voice = None
        self.model_path = self._resolve_model_path()
        self.chunk_chars = int(self.settings.tts.settings.get("chunk_chars", 1200))
        self.chunk_silence_ms = int(self.settings.tts.settings.get("chunk_silence_ms", 300))
        self.output_format = self.settings.tts.output_format.lower()

    def synthesize(self, text: str, output_dir: Path, artifact_name: str) -> TTSArtifact | None:
        cleaned = text.strip()
        if not cleaned:
            return None

        output_dir.mkdir(parents=True, exist_ok=True)
        wav_path = output_dir / f"{artifact_name}.wav"

        with tempfile.TemporaryDirectory(prefix=f"{artifact_name}_", dir=output_dir) as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            chunk_paths = self._synthesize_chunks(cleaned, temp_dir)
            self._combine_wav_files(chunk_paths, wav_path)

        if self.output_format == "wav":
            return TTSArtifact(provider=self.provider_name, path=wav_path)

        if self.output_format == "mp3":
            return TTSArtifact(provider=self.provider_name, path=self._convert_wav_to_mp3(wav_path))

        raise ValueError(f"Formato de audio nao suportado para Piper: {self.settings.tts.output_format}")

    def _resolve_model_path(self) -> Path:
        data_dir = Path(str(self.settings.tts.settings.get("data_dir", "data/voices")))
        if not data_dir.is_absolute():
            data_dir = (self.settings.paths.base / data_dir).resolve()
        data_dir.mkdir(parents=True, exist_ok=True)

        voice_file = str(self.settings.tts.settings.get("voice_file", "")).strip()
        voice_name = str(self.settings.tts.settings.get("voice", "")).strip()

        if voice_file:
            candidate = Path(voice_file)
            if not candidate.is_absolute():
                candidate = (data_dir / candidate).resolve()
            return candidate

        if not voice_name:
            raise ValueError("TTS Piper requer 'tts.settings.voice' ou 'tts.settings.voice_file'")

        return data_dir / f"{voice_name}.onnx"

    def _load_voice(self):
        if self.voice is not None:
            return self.voice

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Modelo Piper nao encontrado: {self.model_path}. Baixe a voz antes de gerar audio."
            )

        piper_module = importlib.import_module("piper")
        self.voice = piper_module.PiperVoice.load(str(self.model_path))
        return self.voice

    def _synthesize_chunks(self, text: str, temp_dir: Path) -> list[Path]:
        voice = self._load_voice()
        text_chunks = chunk_text(text, self.chunk_chars, 0)
        chunk_paths: list[Path] = []

        for index, chunk in enumerate(text_chunks, start=1):
            chunk_path = temp_dir / f"chunk_{index:04d}.wav"
            with wave.open(str(chunk_path), "wb") as wav_file:
                voice.synthesize_wav(chunk.strip(), wav_file)
            chunk_paths.append(chunk_path)

        return chunk_paths

    def _combine_wav_files(self, chunk_paths: list[Path], destination: Path) -> None:
        if not chunk_paths:
            raise ValueError("Nenhum chunk de audio foi gerado pelo Piper")

        with wave.open(str(chunk_paths[0]), "rb") as first_chunk:
            params = first_chunk.getparams()
            sample_rate = first_chunk.getframerate()
            sample_width = first_chunk.getsampwidth()
            channels = first_chunk.getnchannels()
            base_format = (
                first_chunk.getnchannels(),
                first_chunk.getsampwidth(),
                first_chunk.getframerate(),
                first_chunk.getcomptype(),
            )

        silence_frames = int(sample_rate * (self.chunk_silence_ms / 1000))
        silence = b"\x00" * silence_frames * sample_width * channels

        with wave.open(str(destination), "wb") as output_wav:
            output_wav.setparams(params)
            for index, chunk_path in enumerate(chunk_paths, start=1):
                with wave.open(str(chunk_path), "rb") as chunk_wav:
                    chunk_format = (
                        chunk_wav.getnchannels(),
                        chunk_wav.getsampwidth(),
                        chunk_wav.getframerate(),
                        chunk_wav.getcomptype(),
                    )
                    if chunk_format != base_format:
                        raise ValueError("Chunks Piper retornaram formatos de audio incompativeis")
                    output_wav.writeframes(chunk_wav.readframes(chunk_wav.getnframes()))
                if index < len(chunk_paths) and silence:
                    output_wav.writeframes(silence)

    def _convert_wav_to_mp3(self, wav_path: Path) -> Path:
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            raise RuntimeError("Formato mp3 requer ffmpeg instalado e disponivel no PATH")

        from pydub import AudioSegment

        AudioSegment.converter = ffmpeg_path
        mp3_path = wav_path.with_suffix(".mp3")
        AudioSegment.from_wav(wav_path).export(mp3_path, format="mp3")
        wav_path.unlink(missing_ok=True)
        return mp3_path


class PlaceholderTTSProvider:
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

    def synthesize(self, text: str, output_dir: Path, artifact_name: str) -> TTSArtifact | None:
        raise NotImplementedError(f"TTS provider '{self.provider_name}' ainda nao foi implementado")


def build_tts_provider(settings: AppSettings) -> TTSProvider:
    if not settings.tts.enabled or settings.tts.provider.lower() == "disabled":
        return DisabledTTSProvider()
    if settings.tts.provider.lower() == "piper":
        return PiperTTSProvider(settings)
    return PlaceholderTTSProvider(settings.tts.provider)
