from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import shutil

from app.core.config import AppSettings
from app.core.database import JobRepository
from app.core.fs_utils import safe_copy_to_dir, safe_move_to_dir, sha256_file
from app.core.logging_utils import get_job_logger
from app.core.models import BatchRunResult, ExtractedDocument, JobStage, JobStatus
from app.core.text_utils import clean_extracted_text, detect_language
from app.services.extract import DocumentExtractor
from app.services.llm_client import LMStudioClient
from app.services.notifier import Notifier
from app.services.publisher import Publisher
from app.services.tts import TTSArtifact, build_tts_provider


class PipelineRunner:
    def __init__(
        self,
        settings: AppSettings,
        repository: JobRepository,
        logger: logging.Logger,
        extractor: DocumentExtractor | None = None,
        llm_client: LMStudioClient | None = None,
        publisher: Publisher | None = None,
        notifier: Notifier | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.logger = logger
        self.extractor = extractor or DocumentExtractor(settings)
        self.llm_client = llm_client or LMStudioClient(settings)
        self.publisher = publisher or Publisher(settings, repository)
        self.notifier = notifier or Notifier(settings)
        self.tts_provider = build_tts_provider(settings)

    def run_directory(self, input_dir: Path, force: bool = False, limit: int | None = None) -> BatchRunResult:
        result = BatchRunResult()
        files = sorted(
            path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in self.settings.worker.extensoes_aceitas
        )
        if limit is not None:
            files = files[:limit]

        for source_file in files:
            result.processed += 1
            status = self._process_source_file(source_file, force=force)
            if status == JobStatus.COMPLETED:
                result.completed += 1
            elif status == JobStatus.DUPLICATE:
                result.duplicates += 1
            else:
                result.failed += 1

        if result.processed:
            self.notifier.notify_batch(result)
        return result

    def retry_failed(self) -> BatchRunResult:
        result = BatchRunResult()
        for job in self.repository.list_retryable_jobs():
            result.processed += 1
            self.repository.increment_retry(job.id)
            status = self._process_existing_job(job.id)
            if status == JobStatus.COMPLETED:
                result.completed += 1
            else:
                result.failed += 1
        if result.processed:
            self.notifier.notify_batch(result, prefix="Retry concluido")
        return result

    def _process_source_file(self, source_file: Path, force: bool) -> str:
        source_hash = sha256_file(source_file)
        latest = self.repository.find_latest_by_hash(source_hash)
        if latest and latest.status == JobStatus.COMPLETED and not force:
            job_id = self.repository.create_job(
                source_path=str(source_file),
                source_hash=source_hash,
                source_type=source_file.suffix.lower(),
                status=JobStatus.DUPLICATE,
                stage=JobStage.QUEUED,
            )
            safe_move_to_dir(source_file, self.settings.paths.concluidos)
            self.repository.update_job(job_id, finished_at=self._now())
            self.logger.info("Arquivo duplicado ignorado: %s", source_file.name)
            return JobStatus.DUPLICATE

        if latest and latest.status in (JobStatus.FAILED, JobStatus.PROCESSING) and not force:
            workspace = self._workspace_dir(latest.id)
            workspace_source = self._workspace_source_file(workspace)
            if workspace_source is None:
                workspace.joinpath("source").mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_file), workspace / "source" / source_file.name)
            else:
                safe_move_to_dir(source_file, self.settings.paths.concluidos)
            self.logger.info("Retomando job existente %s para %s", latest.id, source_file.name)
            return self._process_existing_job(latest.id)

        job_id = self.repository.create_job(
            source_path=str(source_file),
            source_hash=source_hash,
            source_type=source_file.suffix.lower(),
            status=JobStatus.PROCESSING,
            stage=JobStage.INGESTED,
        )
        workspace = self._workspace_dir(job_id)
        workspace.joinpath("source").mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_file), workspace / "source" / source_file.name)
        self.logger.info("Job %s criado para %s", job_id, source_file.name)
        return self._process_existing_job(job_id)

    def _process_existing_job(self, job_id: int) -> str:
        job = self.repository.get_job(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} nao encontrado")

        workspace = self._workspace_dir(job_id)
        workspace.mkdir(parents=True, exist_ok=True)
        artifacts_dir = workspace / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        log_path = workspace / "job.log"
        job_logger = get_job_logger(job_id, log_path)
        source_copy = self._workspace_source_file(workspace)

        try:
            if source_copy is None:
                raise FileNotFoundError(f"Arquivo fonte nao encontrado em {workspace / 'source'}")

            self.repository.update_job(job_id, status=JobStatus.PROCESSING, error_code=None, error_message=None)
            warnings: list[str] = []
            extracted_doc = self._load_or_extract(job_id, source_copy, artifacts_dir, warnings, job_logger)
            normalized_path = self._ensure_normalized(job_id, extracted_doc, artifacts_dir)
            clean_text_path = self._ensure_clean_text(job_id, extracted_doc, normalized_path, artifacts_dir)
            summary_path = self._ensure_summary(job_id, clean_text_path, artifacts_dir)
            tts_artifacts = self._ensure_tts(clean_text_path, summary_path, artifacts_dir)
            published_dir = self.publisher.publish_job(
                job_id=job_id,
                source_copy=source_copy,
                clean_text_path=clean_text_path,
                summary_path=summary_path,
                log_path=log_path,
                warnings=warnings,
                llm_model=self.llm_client.model_name,
                tts_artifacts=tts_artifacts,
            )
            self.repository.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                stage=JobStage.PUBLISHED,
                finished_at=self._now(),
            )
            safe_copy_to_dir(source_copy, self.settings.paths.concluidos)
            self.notifier.notify_success(job_id, source_copy.name, str(published_dir))
            job_logger.info("Job %s concluido com sucesso", job_id)
            return JobStatus.COMPLETED
        except Exception as exc:
            self.repository.update_job(
                job_id,
                status=JobStatus.FAILED,
                stage=JobStage.FAILED,
                error_code=type(exc).__name__,
                error_message=str(exc),
                finished_at=self._now(),
            )
            if source_copy is not None:
                safe_copy_to_dir(source_copy, self.settings.paths.falhas)
                self.notifier.notify_failure(job_id, source_copy.name, str(exc))
            job_logger.exception("Job %s falhou: %s", job_id, exc)
            self.logger.exception("Job %s falhou", job_id)
            return JobStatus.FAILED

    def _load_or_extract(
        self,
        job_id: int,
        source_copy: Path,
        artifacts_dir: Path,
        warnings: list[str],
        job_logger: logging.Logger,
    ) -> ExtractedDocument:
        raw_path = artifacts_dir / "raw_extracted.md"
        meta_path = artifacts_dir / "raw_extracted.meta.json"
        if raw_path.exists() and meta_path.exists():
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            restored = ExtractedDocument(
                source_path=source_copy,
                source_type=metadata["source_type"],
                title=metadata["title"],
                raw_text=raw_path.read_text(encoding="utf-8"),
                sections=[],
                language_hint=metadata.get("language_hint"),
                pages_or_sections=metadata.get("pages_or_sections"),
                warnings=metadata.get("warnings", []),
                metadata=metadata.get("metadata", {}),
            )
            warnings.extend(restored.warnings)
            return restored

        extracted = self.extractor.extract(source_copy)
        raw_path.write_text(extracted.raw_text, encoding="utf-8")
        meta_path.write_text(
            json.dumps(
                {
                    "source_type": extracted.source_type,
                    "title": extracted.title,
                    "language_hint": extracted.language_hint,
                    "pages_or_sections": extracted.pages_or_sections,
                    "warnings": extracted.warnings,
                    "metadata": extracted.metadata,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        warnings.extend(extracted.warnings)
        self.repository.update_job(
            job_id,
            stage=JobStage.EXTRACTED,
            language_detected=extracted.language_hint or detect_language(extracted.raw_text),
            pages_or_sections=extracted.pages_or_sections or len(extracted.sections),
        )
        job_logger.info("Extracao concluida")
        return extracted

    def _ensure_normalized(self, job_id: int, extracted_doc: ExtractedDocument, artifacts_dir: Path) -> Path:
        normalized_path = artifacts_dir / "normalized.md"
        if not normalized_path.exists():
            normalized_path.write_text(clean_extracted_text(extracted_doc.raw_text), encoding="utf-8")
            self.repository.update_job(job_id, stage=JobStage.NORMALIZED)
        return normalized_path

    def _ensure_clean_text(self, job_id: int, extracted_doc: ExtractedDocument, normalized_path: Path, artifacts_dir: Path) -> Path:
        clean_text_path = artifacts_dir / "texto_limpo.txt"
        if not clean_text_path.exists():
            normalized_text = normalized_path.read_text(encoding="utf-8")
            clean_text = self.llm_client.generate_clean_text(
                title=extracted_doc.title,
                source_type=extracted_doc.source_type,
                text=normalized_text,
                source_language=extracted_doc.language_hint or detect_language(normalized_text),
            )
            clean_text_path.write_text(clean_text, encoding="utf-8")
            self.repository.update_job(job_id, stage=JobStage.CLEANED)
        return clean_text_path

    def _ensure_summary(self, job_id: int, clean_text_path: Path, artifacts_dir: Path) -> Path:
        summary_path = artifacts_dir / "resumo.txt"
        if not summary_path.exists():
            summary = self.llm_client.generate_summary(clean_text_path.read_text(encoding="utf-8"))
            summary_path.write_text(summary, encoding="utf-8")
            self.repository.update_job(job_id, stage=JobStage.SUMMARIZED)
        return summary_path

    def _ensure_tts(self, clean_text_path: Path, summary_path: Path, artifacts_dir: Path) -> list[TTSArtifact]:
        audio_dir = artifacts_dir / "audio"
        artifacts: list[TTSArtifact] = []
        for name, text_path in (("narracao", clean_text_path), ("resumo", summary_path)):
            artifact = self.tts_provider.synthesize(
                text=text_path.read_text(encoding="utf-8"),
                output_dir=audio_dir,
                artifact_name=name,
            )
            if artifact is not None:
                artifacts.append(artifact)
        return artifacts

    def _workspace_dir(self, job_id: int) -> Path:
        return self.settings.paths.processando / f"{job_id:06d}"

    @staticmethod
    def _workspace_source_file(workspace: Path) -> Path | None:
        source_dir = workspace / "source"
        if not source_dir.exists():
            return None
        files = [path for path in source_dir.iterdir() if path.is_file()]
        return files[0] if files else None

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
