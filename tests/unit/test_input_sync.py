from app.core.config import load_settings
from app.core.database import JobRepository
from app.services.input_sync import sync_source_dir_to_queue

from tests.conftest import write_config_bundle


def test_sync_source_dir_to_queue_imports_only_new_files(tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    repository = JobRepository(settings.paths.db)

    source_dir = tmp_path / "drive"
    source_dir.mkdir()
    (source_dir / "artigo-a.pdf").write_text("conteudo A", encoding="utf-8")
    (source_dir / "artigo-b.txt").write_text("conteudo B", encoding="utf-8")

    result = sync_source_dir_to_queue(
        source_dir=source_dir,
        queue_dir=settings.paths.entrada,
        repository=repository,
        accepted_extensions=settings.worker.extensoes_aceitas,
    )

    assert result.discovered == 2
    assert result.imported == 2
    assert result.skipped_completed == 0
    assert result.skipped_queued == 0
    assert len(list(settings.paths.entrada.iterdir())) == 2


def test_sync_source_dir_to_queue_skips_completed_hashes(tmp_path) -> None:
    write_config_bundle(tmp_path)
    settings = load_settings(tmp_path)
    repository = JobRepository(settings.paths.db)

    source_dir = tmp_path / "drive"
    source_dir.mkdir()
    source_file = source_dir / "artigo.pdf"
    source_file.write_text("conteudo repetido", encoding="utf-8")

    from app.core.fs_utils import sha256_file

    repository.create_job(
        source_path=str(source_file),
        source_hash=sha256_file(source_file),
        source_type=source_file.suffix.lower(),
        status="completed",
        stage="published",
    )

    result = sync_source_dir_to_queue(
        source_dir=source_dir,
        queue_dir=settings.paths.entrada,
        repository=repository,
        accepted_extensions=settings.worker.extensoes_aceitas,
    )

    assert result.discovered == 1
    assert result.imported == 0
    assert result.skipped_completed == 1
    assert result.skipped_queued == 0
    assert list(settings.paths.entrada.iterdir()) == []
