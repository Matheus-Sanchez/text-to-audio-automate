import wave

from app.core.config import load_settings
from app.services.tts import DisabledTTSProvider, PiperTTSProvider, build_tts_provider

from tests.conftest import write_config_bundle


def test_disabled_tts_provider_returns_none(tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    provider = build_tts_provider(settings)
    assert isinstance(provider, DisabledTTSProvider)
    assert provider.synthesize("texto", tmp_path / "audio", "narracao") is None


def test_build_tts_provider_returns_piper_provider(tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    settings.tts.enabled = True
    settings.tts.provider = "piper"
    provider = build_tts_provider(settings)
    assert isinstance(provider, PiperTTSProvider)


def test_piper_provider_combines_chunk_audio(monkeypatch, tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    settings.tts.enabled = True
    settings.tts.provider = "piper"
    settings.tts.output_format = "wav"
    settings.tts.settings["data_dir"] = str(tmp_path / "voices")
    settings.tts.settings["voice_file"] = str(tmp_path / "voices" / "fake.onnx")
    settings.tts.settings["chunk_chars"] = 20
    settings.tts.settings["chunk_silence_ms"] = 0

    model_path = tmp_path / "voices" / "fake.onnx"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"fake")

    class FakeVoice:
        def synthesize_wav(self, text, wav_file):
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x01\x02" * max(1, len(text)))

    provider = PiperTTSProvider(settings)
    monkeypatch.setattr(provider, "_load_voice", lambda: FakeVoice())

    artifact = provider.synthesize(
        "Primeiro trecho.\n\nSegundo trecho com mais conteudo para dividir.",
        tmp_path / "audio",
        "narracao",
    )

    assert artifact is not None
    assert artifact.path.exists()
    with wave.open(str(artifact.path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getnframes() > 0
