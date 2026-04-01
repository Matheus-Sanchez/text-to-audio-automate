from __future__ import annotations

import argparse

from app.core.config import load_settings
from app.core.database import JobRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mostra historico de jobs")
    parser.add_argument("--last", type=int, default=20, help="Quantidade de jobs a listar")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = load_settings()
    repository = JobRepository(settings.paths.db)
    jobs = repository.list_jobs(limit=args.last)
    if not jobs:
        print("Nenhum job encontrado.")
        return 0
    print("id | status | stage | retries | source")
    print("-" * 80)
    for job in jobs:
        print(f"{job.id} | {job.status} | {job.stage} | {job.retry_count} | {job.source_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
