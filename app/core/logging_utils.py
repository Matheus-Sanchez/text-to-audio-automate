from __future__ import annotations

import logging
from pathlib import Path


def configure_console_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("article_to_audio")
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(handler)
    return logger


def get_job_logger(job_id: int, log_file: Path) -> logging.Logger:
    logger_name = f"article_to_audio.job.{job_id}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_file for handler in logger.handlers):
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(file_handler)
    return logger
