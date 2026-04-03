from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import load_settings
from app.core.database import JobRepository
from app.core.logging_utils import configure_console_logging
from app.core.pipeline import PipelineRunner
from app.services.input_sync import sync_source_dir_to_queue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Processa documentos da pasta de entrada")
    parser.add_argument("--input", type=Path, default=Path("data/entrada"), help="Pasta de entrada")
    parser.add_argument(
        "--sync-from",
        type=Path,
        default=None,
        help="Copia artigos de uma pasta externa para a fila interna antes de processar",
    )
    parser.add_argument("--force", action="store_true", help="Reprocessa mesmo se houver duplicados")
    parser.add_argument("--limit", type=int, default=None, help="Limita quantos arquivos processar")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = load_settings()
    logger = configure_console_logging()
    repository = JobRepository(settings.paths.db)
    runner = PipelineRunner(settings, repository, logger)
    input_dir = args.input
    if not input_dir.is_absolute():
        input_dir = (settings.paths.base / input_dir).resolve()
    input_dir.mkdir(parents=True, exist_ok=True)

    sync_source = args.sync_from or settings.paths.fonte_artigos
    if sync_source is not None:
        if not sync_source.is_absolute():
            sync_source = (settings.paths.base / sync_source).resolve()
        sync_result = sync_source_dir_to_queue(
            source_dir=sync_source,
            queue_dir=input_dir,
            repository=repository,
            accepted_extensions=settings.worker.extensoes_aceitas,
        )
        logger.info(
            "Importacao concluida | encontrados=%s importados=%s ja_processados=%s ja_na_fila=%s origem=%s",
            sync_result.discovered,
            sync_result.imported,
            sync_result.skipped_completed,
            sync_result.skipped_queued,
            sync_source,
        )

    result = runner.run_directory(input_dir, force=args.force, limit=args.limit)
    logger.info(
        "Lote finalizado | processados=%s concluidos=%s falhas=%s duplicados=%s",
        result.processed,
        result.completed,
        result.failed,
        result.duplicates,
    )
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
