from app.core.config import load_settings
from app.services.tts import DisabledTTSProvider, build_tts_provider

from tests.conftest import write_config_bundle


def test_disabled_tts_provider_returns_none(tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    provider = build_tts_provider(settings)
    assert isinstance(provider, DisabledTTSProvider)
    assert provider.synthesize("texto", tmp_path / "audio", "narracao") is None
