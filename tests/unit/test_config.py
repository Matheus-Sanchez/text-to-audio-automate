from app.core.config import load_settings

from tests.conftest import write_config_bundle


def test_load_settings_resolves_paths(tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    assert settings.paths.entrada.exists()
    assert settings.tts.enabled is False
    assert settings.llm.model is None
