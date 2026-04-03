from __future__ import annotations

from functools import cached_property
import json
from typing import Any

import requests

from app.core.config import AppSettings
from app.core.text_utils import chunk_text


class LMStudioClient:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.settings.llm.api_key}"})

    @cached_property
    def model_name(self) -> str:
        configured = (self.settings.llm.model or "").strip()
        if configured and configured.lower() not in {"auto", "local-model"}:
            return configured
        models = self.list_models()
        if not models:
            raise RuntimeError("LM Studio nao retornou nenhum modelo em /models")
        return models[0]

    def list_models(self) -> list[str]:
        response = self.session.get(f"{self.settings.llm.url_base}/models", timeout=self.settings.llm.timeout_segundos)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        return [item["id"] for item in data if item.get("id")]

    def generate_clean_text(self, title: str, source_type: str, text: str, source_language: str | None) -> str:
        if not text.strip():
            return ""
        chunks = chunk_text(text, self.settings.llm.chunk_chars, self.settings.llm.overlap_chars)
        outputs = []
        for index, chunk in enumerate(chunks, start=1):
            user_prompt = (
                f"Titulo: {title}\n"
                f"Tipo: {source_type}\n"
                f"Idioma de origem: {source_language or 'desconhecido'}\n"
                f"Chunk: {index}/{len(chunks)}\n\n"
                f"{self.settings.llm_prompts.get('leitura_integral', '')}\n\n"
                f"Trecho:\n{chunk}"
            )
            outputs.append(self._chat(user_prompt=user_prompt, mode="leitura_integral"))
        return "\n\n".join(part.strip() for part in outputs if part.strip()).strip()

    def generate_summary(self, clean_text: str) -> str:
        if not clean_text.strip():
            return ""
        chunks = chunk_text(clean_text, self.settings.llm.chunk_chars, self.settings.llm.overlap_chars)
        if len(chunks) == 1:
            return self._summarize_block(chunks[0], prompt_key="resumo", label="Documento")

        partial_summaries = [
            self._summarize_block(
                chunk,
                prompt_key="resumo_parcial",
                label=f"Trecho {index}/{len(chunks)}",
            )
            for index, chunk in enumerate(chunks, start=1)
        ]
        return self._reduce_summaries(partial_summaries)

    def _reduce_summaries(self, summaries: list[str]) -> str:
        current = [summary.strip() for summary in summaries if summary.strip()]
        if not current:
            return ""

        for _ in range(6):
            if len(current) == 1:
                return current[0]

            grouped = self._group_summary_batches(current)
            if len(grouped) == 1:
                return self._summarize_block(grouped[0], prompt_key="resumo_consolidado", label="Resumos parciais")

            current = [
                self._summarize_block(
                    batch,
                    prompt_key="resumo_consolidado",
                    label=f"Lote de resumos {index}/{len(grouped)}",
                )
                for index, batch in enumerate(grouped, start=1)
            ]

        return current[0]

    def _group_summary_batches(self, summaries: list[str]) -> list[str]:
        batches: list[str] = []
        current = ""

        for index, summary in enumerate(summaries, start=1):
            block = f"Resumo parcial {index}:\n{summary.strip()}"
            candidate = f"{current}\n\n{block}".strip() if current else block
            if len(candidate) <= self.settings.llm.chunk_chars:
                current = candidate
                continue

            if current:
                batches.append(current)
                current = block
                continue

            batches.extend(chunk_text(block, self.settings.llm.chunk_chars, self.settings.llm.overlap_chars))
            current = ""

        if current:
            batches.append(current)
        return batches

    def _summarize_block(self, text: str, *, prompt_key: str, label: str) -> str:
        prompt = self.settings.llm_prompts.get(prompt_key) or self.settings.llm_prompts.get("resumo", "")
        user_prompt = f"{prompt}\n\n{label}:\n{text}"
        return self._chat(user_prompt=user_prompt, mode="resumo").strip()

    def _chat(self, *, user_prompt: str, mode: str) -> str:
        mode_settings = self.settings.llm_modes.get(mode, {})
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.settings.llm_prompts.get("sistema_base", "")},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": mode_settings.get("temperatura", self.settings.llm.temperatura_padrao),
            "max_tokens": mode_settings.get("max_tokens", 2048),
        }
        response = self.session.post(
            f"{self.settings.llm.url_base}/chat/completions",
            json=payload,
            timeout=self.settings.llm.timeout_segundos,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = self._extract_error_detail(response)
            if detail:
                raise requests.HTTPError(f"{exc} | detalhe={detail}", response=response) from exc
            raise
        content = response.json()["choices"][0]["message"]["content"]
        return self._sanitize(content)

    @staticmethod
    def _sanitize(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                text = "\n".join(lines[1:-1]).strip()
        return text

    @staticmethod
    def _extract_error_detail(response: requests.Response) -> str:
        try:
            payload = response.json()
            detail = json.dumps(payload, ensure_ascii=False)
        except ValueError:
            detail = response.text.strip()
        detail = " ".join(detail.split())
        return detail[:500]
