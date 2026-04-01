import requests

from app.core.config import load_settings
from app.services.llm_client import LMStudioClient

from tests.conftest import write_config_bundle


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")

    def json(self):
        return self._payload


def test_lmstudio_client_uses_models_endpoint(monkeypatch, tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    client = LMStudioClient(settings)

    def fake_get(url, timeout):
        assert url.endswith("/models")
        return DummyResponse({"data": [{"id": "model-a"}]})

    def fake_post(url, json, timeout):
        assert url.endswith("/chat/completions")
        assert json["model"] == "model-a"
        return DummyResponse({"choices": [{"message": {"content": "texto limpo"}}]})

    monkeypatch.setattr(client.session, "get", fake_get)
    monkeypatch.setattr(client.session, "post", fake_post)

    assert client.generate_clean_text("Titulo", ".txt", "conteudo", "pt-BR") == "texto limpo"
