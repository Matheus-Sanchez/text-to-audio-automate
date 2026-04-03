from app.core.config import load_settings
from app.core.database import JobRepository
from app.core.logging_utils import configure_console_logging
from app.core.pipeline import PipelineRunner
from app.services.llm_client import LMStudioClient

from tests.conftest import write_config_bundle


class FakeLLMClient:
    model_name = "fake-model"

    def generate_clean_text(self, title, source_type, text, source_language):
        return f"LIMPO: {text.strip()}"

    def generate_summary(self, clean_text):
        return "RESUMO: texto sintetizado"


def test_pipeline_text_only_publish(tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    input_file = settings.paths.entrada / "documento.txt"
    input_file.write_text("Titulo\n\nConteudo do documento.", encoding="utf-8")

    repository = JobRepository(settings.paths.db)
    logger = configure_console_logging()
    runner = PipelineRunner(settings, repository, logger, llm_client=FakeLLMClient())
    result = runner.run_directory(settings.paths.entrada)

    assert result.completed == 1
    published = list(settings.paths.saida_sync.iterdir())
    assert len(published) == 1
    package = published[0]
    assert (package / "texto_limpo.txt").exists()
    assert (package / "resumo.txt").exists()
    assert (package / "manifest.json").exists()
    assert (package / "job.log").exists()
