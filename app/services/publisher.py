from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
from typing import Any

from app.core.config import AppSettings
from app.core.database import JobRepository
from app.core.fs_utils import copytree_atomic, sha256_file, slugify
from app.services.tts import TTSArtifact


class Publisher:
    def __init__(self, settings: AppSettings, repository: JobRepository) -> None:
        self.settings = settings
        self.repository = repository

    def publish_job(
        self,
        *,
        job_id: int,
        source_copy: Path,
        clean_text_path: Path,
        summary_path: Path,
        log_path: Path,
        warnings: list[str],
        llm_model: str,
        tts_artifacts: list[TTSArtifact],
    ) -> Path:
        package_name = f"{slugify(source_copy.stem)}__{job_id:06d}"
        local_package = self.settings.paths.temp / "publish" / package_name
        if local_package.exists():
            shutil.rmtree(local_package)
        local_package.mkdir(parents=True, exist_ok=True)

        copied_artifacts: dict[str, Path] = {}
        copied_artifacts["texto_limpo.md"] = self._copy_artifact(clean_text_path, local_package / "texto_limpo.md")
        copied_artifacts["resumo.md"] = self._copy_artifact(summary_path, local_package / "resumo.md")
        copied_artifacts["job.log"] = self._copy_artifact(log_path, local_package / "job.log")

        for artifact in tts_artifacts:
            copied_artifacts[artifact.path.name] = self._copy_artifact(artifact.path, local_package / artifact.path.name)

        artifact_records = []
        for relative_name, artifact_path in copied_artifacts.items():
            checksum = sha256_file(artifact_path)
            size_bytes = artifact_path.stat().st_size
            artifact_records.append(
                {
                    "artifact_type": relative_name,
                    "relative_path": relative_name,
                    "size_bytes": size_bytes,
                    "checksum": checksum,
                }
            )
            self.repository.add_artifact(job_id, relative_name, relative_name, size_bytes, checksum)

        manifest = {
            "job_id": job_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "source": {
                "name": source_copy.name,
                "path": str(source_copy),
                "hash": sha256_file(source_copy),
                "type": source_copy.suffix.lower(),
            },
            "llm": {
                "base_url": self.settings.llm.url_base,
                "model": llm_model,
            },
            "tts": {
                "enabled": self.settings.tts.enabled,
                "provider": self.settings.tts.provider,
                "output_format": self.settings.tts.output_format,
            },
            "warnings": warnings,
            "artifacts": artifact_records,
        }
        manifest_path = local_package / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.repository.add_artifact(job_id, "manifest.json", "manifest.json", manifest_path.stat().st_size, sha256_file(manifest_path))

        published_dir = copytree_atomic(local_package, self.settings.paths.saida_sync / package_name)
        return published_dir

    @staticmethod
    def _copy_artifact(source: Path, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination
