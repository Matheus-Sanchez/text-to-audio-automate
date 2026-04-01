from __future__ import annotations

from app.core.config import AppSettings
from app.core.models import BatchRunResult

import requests


class Notifier:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def notify_success(self, job_id: int, filename: str, published_dir: str) -> None:
        self._send(
            title=f"Job {job_id} concluido",
            message=f"Arquivo: {filename}\nPublicado em: {published_dir}",
            priority="default",
        )

    def notify_failure(self, job_id: int, filename: str, error_message: str) -> None:
        self._send(
            title=f"Job {job_id} falhou",
            message=f"Arquivo: {filename}\nErro: {error_message}",
            priority="high",
        )

    def notify_batch(self, result: BatchRunResult, prefix: str = "Lote concluido") -> None:
        self._send(
            title=prefix,
            message=(
                f"Processados: {result.processed}\n"
                f"Concluidos: {result.completed}\n"
                f"Falhas: {result.failed}\n"
                f"Duplicados: {result.duplicates}"
            ),
            priority="default",
        )

    def _send(self, *, title: str, message: str, priority: str) -> None:
        if not self.settings.notifications.ativo or not self.settings.notifications.canal_ntfy:
            return
        try:
            response = requests.post(
                f"{self.settings.notifications.url_ntfy}/{self.settings.notifications.canal_ntfy}",
                data=message.encode("utf-8"),
                headers={"Title": title, "Priority": priority},
                timeout=10,
            )
            response.raise_for_status()
        except Exception:
            return
