from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.database import JobRepository
from app.core.fs_utils import safe_copy_to_dir, sha256_file
from app.core.models import JobStatus


@dataclass(slots=True)
class InputSyncResult:
    discovered: int = 0
    imported: int = 0
    skipped_completed: int = 0
    skipped_queued: int = 0


def sync_source_dir_to_queue(
    *,
    source_dir: Path,
    queue_dir: Path,
    repository: JobRepository,
    accepted_extensions: tuple[str, ...],
) -> InputSyncResult:
    if not source_dir.exists():
        raise FileNotFoundError(f"Pasta de origem nao encontrada: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"A origem configurada nao e uma pasta: {source_dir}")

    queue_dir.mkdir(parents=True, exist_ok=True)
    queued_hashes = {
        sha256_file(path)
        for path in queue_dir.iterdir()
        if path.is_file() and path.suffix.lower() in accepted_extensions
    }

    result = InputSyncResult()
    current_batch_hashes: set[str] = set()
    source_files = sorted(
        path for path in source_dir.rglob("*") if path.is_file() and path.suffix.lower() in accepted_extensions
    )

    for source_file in source_files:
        result.discovered += 1
        source_hash = sha256_file(source_file)

        if source_hash in current_batch_hashes or source_hash in queued_hashes:
            result.skipped_queued += 1
            continue

        latest = repository.find_latest_by_hash(source_hash)
        if latest and latest.status == JobStatus.COMPLETED:
            result.skipped_completed += 1
            continue

        safe_copy_to_dir(source_file, queue_dir)
        current_batch_hashes.add(source_hash)
        queued_hashes.add(source_hash)
        result.imported += 1

    return result
