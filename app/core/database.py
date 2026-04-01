from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.core.models import JobRecord


class JobRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    language_detected TEXT,
                    pages_or_sections INTEGER,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    error_code TEXT,
                    error_message TEXT,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_hash ON jobs(source_hash);
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    artifact_type TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
                """
            )

    def create_job(self, *, source_path: str, source_hash: str, source_type: str, status: str, stage: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO jobs (source_path, source_hash, source_type, status, stage) VALUES (?, ?, ?, ?, ?)",
                (source_path, source_hash, source_type, status, stage),
            )
            return int(cursor.lastrowid)

    def update_job(self, job_id: int, **fields: Any) -> None:
        if not fields:
            return
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [job_id]
        with self._connect() as connection:
            connection.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", values)

    def increment_retry(self, job_id: int) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE jobs SET retry_count = retry_count + 1 WHERE id = ?", (job_id,))

    def get_job(self, job_id: int) -> JobRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return JobRecord(**dict(row)) if row else None

    def list_jobs(self, limit: int = 20) -> list[JobRecord]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [JobRecord(**dict(row)) for row in rows]

    def list_retryable_jobs(self) -> list[JobRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE status IN ('failed', 'processing') ORDER BY id ASC"
            ).fetchall()
        return [JobRecord(**dict(row)) for row in rows]

    def find_latest_by_hash(self, source_hash: str) -> JobRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE source_hash = ? ORDER BY id DESC LIMIT 1",
                (source_hash,),
            ).fetchone()
        return JobRecord(**dict(row)) if row else None

    def add_artifact(self, job_id: int, artifact_type: str, relative_path: str, size_bytes: int, checksum: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO artifacts (job_id, artifact_type, relative_path, size_bytes, checksum) VALUES (?, ?, ?, ?, ?)",
                (job_id, artifact_type, relative_path, size_bytes, checksum),
            )

    def list_artifacts(self, job_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT artifact_type, relative_path, size_bytes, checksum, created_at FROM artifacts WHERE job_id = ? ORDER BY id ASC",
                (job_id,),
            ).fetchall()
        return [dict(row) for row in rows]
