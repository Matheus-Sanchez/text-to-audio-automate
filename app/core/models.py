from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class JobStage(StrEnum):
    QUEUED = "queued"
    INGESTED = "ingested"
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    CLEANED = "cleaned"
    SUMMARIZED = "summarized"
    TTS = "tts"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass(slots=True)
class Section:
    heading: str | None
    content: str
    order: int
    source_ref: str | None = None


@dataclass(slots=True)
class ExtractedDocument:
    source_path: Path
    source_type: str
    title: str
    raw_text: str
    sections: list[Section]
    language_hint: str | None = None
    pages_or_sections: int | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class JobRecord:
    id: int
    source_path: str
    source_hash: str
    source_type: str
    status: str
    stage: str
    language_detected: str | None
    pages_or_sections: int | None
    retry_count: int
    error_code: str | None
    error_message: str | None
    started_at: str | None
    finished_at: str | None


@dataclass(slots=True)
class BatchRunResult:
    processed: int = 0
    completed: int = 0
    failed: int = 0
    duplicates: int = 0
    warnings: list[str] = field(default_factory=list)
