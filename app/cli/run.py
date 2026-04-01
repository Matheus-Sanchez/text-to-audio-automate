from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import load_settings
from app.core.database import JobRepository
from app.core.logging_utils import configure_console_logging
from app.core.pipeline import PipelineRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Processa documentos da pasta de entrada")
    parser.add_argument("--input", type=Path, default=Path("data/entrada"), help="Pasta de entrada")
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
