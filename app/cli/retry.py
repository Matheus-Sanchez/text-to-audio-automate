from __future__ import annotations

import argparse

from app.core.config import load_settings
from app.core.database import JobRepository
from app.core.logging_utils import configure_console_logging
from app.core.pipeline import PipelineRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Retoma jobs falhos ou interrompidos")
    parser.add_argument("--failed", action="store_true", help="Retenta jobs com status failed/processing")
    return parser


def main() -> int:
    build_parser().parse_args()
    settings = load_settings()
    logger = configure_console_logging()
    repository = JobRepository(settings.paths.db)
    runner = PipelineRunner(settings, repository, logger)
    result = runner.retry_failed()
    logger.info(
        "Retry finalizado | processados=%s concluidos=%s falhas=%s",
        result.processed,
        result.completed,
        result.failed,
    )
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
