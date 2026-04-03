from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


def _expand_path(raw: str, base: Path) -> Path:
    candidate = Path(os.path.expandvars(raw))
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


@dataclass(slots=True)
class ProjectConfig:
    name: str
    version: str


@dataclass(slots=True)
class PathsConfig:
    base: Path
    entrada: Path
    fonte_artigos: Path | None
    processando: Path
    concluidos: Path
    falhas: Path
    saida_audio: Path
    saida_sync: Path
    temp: Path
    logs: Path
    db: Path


@dataclass(slots=True)
class TesseractConfig:
    executavel: Path
    idioma: str
    confianca_minima: int
    fallback_chars_minimos: int


@dataclass(slots=True)
class LLMConfig:
    url_base: str
    model: str | None
    api_key: str
    timeout_segundos: int
    contexto_maximo: int
    chunk_chars: int
    overlap_chars: int
    temperatura_padrao: float


@dataclass(slots=True)
class TTSConfig:
    enabled: bool
    provider: str
    output_format: str
    settings: dict[str, Any]


@dataclass(slots=True)
class NotificationsConfig:
    canal_ntfy: str
    url_ntfy: str
    ativo: bool


@dataclass(slots=True)
class WorkerConfig:
    max_retries_por_job: int
    extensoes_aceitas: tuple[str, ...]


@dataclass(slots=True)
class AppSettings:
    project_root: Path
    project: ProjectConfig
    paths: PathsConfig
    tesseract: TesseractConfig
    llm: LLMConfig
    tts: TTSConfig
    notifications: NotificationsConfig
    worker: WorkerConfig
    llm_modes: dict[str, Any]
    llm_prompts: dict[str, str]
    voice_profiles: dict[str, Any]

    def ensure_directories(self) -> None:
        for directory in (
            self.paths.base,
            self.paths.entrada,
            self.paths.processando,
            self.paths.concluidos,
            self.paths.falhas,
            self.paths.saida_audio,
            self.paths.saida_sync,
            self.paths.temp,
            self.paths.logs,
            self.paths.db.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_settings(project_root: Path | None = None) -> AppSettings:
    root = project_root or Path(__file__).resolve().parents[2]
    config_dir = root / "config"
    app_raw = _read_yaml(config_dir / "app.yaml")
    llm_raw = _read_yaml(config_dir / "llm.yaml")
    voices_raw = _read_yaml(config_dir / "voices.yaml")

    base = _expand_path(app_raw["caminhos"]["base"], root)
    settings = AppSettings(
        project_root=root,
        project=ProjectConfig(
            name=str(app_raw["projeto"]["nome"]),
            version=str(app_raw["projeto"]["versao"]),
        ),
        paths=PathsConfig(
            base=base,
            entrada=_expand_path(app_raw["caminhos"]["entrada"], base),
            fonte_artigos=(
                _expand_path(str(app_raw["caminhos"].get("fonte_artigos", "")).strip(), base)
                if str(app_raw["caminhos"].get("fonte_artigos", "")).strip()
                else None
            ),
            processando=_expand_path(app_raw["caminhos"]["processando"], base),
            concluidos=_expand_path(app_raw["caminhos"]["concluidos"], base),
            falhas=_expand_path(app_raw["caminhos"]["falhas"], base),
            saida_audio=_expand_path(app_raw["caminhos"]["saida_audio"], base),
            saida_sync=_expand_path(app_raw["caminhos"]["saida_sync"], base),
            temp=_expand_path(app_raw["caminhos"]["temp"], base),
            logs=_expand_path(app_raw["caminhos"]["logs"], base),
            db=_expand_path(app_raw["banco"]["caminho"], base),
        ),
        tesseract=TesseractConfig(
            executavel=_expand_path(app_raw["tesseract"]["executavel"], base),
            idioma=str(app_raw["tesseract"]["idioma"]),
            confianca_minima=int(app_raw["tesseract"]["confianca_minima"]),
            fallback_chars_minimos=int(app_raw["tesseract"].get("fallback_chars_minimos", 80)),
        ),
        llm=LLMConfig(
            url_base=str(app_raw["llm"]["url_base"]).rstrip("/"),
            model=(str(app_raw["llm"].get("model") or "").strip() or None),
            api_key=str(app_raw["llm"].get("api_key", "lm-studio")),
            timeout_segundos=int(app_raw["llm"].get("timeout_segundos", 120)),
            contexto_maximo=int(app_raw["llm"].get("contexto_maximo", 8192)),
            chunk_chars=int(app_raw["llm"].get("chunk_chars", 3500)),
            overlap_chars=int(app_raw["llm"].get("overlap_chars", 250)),
            temperatura_padrao=float(app_raw["llm"].get("temperatura_padrao", 0.2)),
        ),
        tts=TTSConfig(
            enabled=bool(app_raw["tts"].get("enabled", False)),
            provider=str(app_raw["tts"].get("provider", "disabled")),
            output_format=str(app_raw["tts"].get("output_format", "mp3")),
            settings=dict(app_raw["tts"].get("settings", {})),
        ),
        notifications=NotificationsConfig(
            canal_ntfy=str(app_raw["notificacoes"].get("canal_ntfy", "")),
            url_ntfy=str(app_raw["notificacoes"].get("url_ntfy", "https://ntfy.sh")).rstrip("/"),
            ativo=bool(app_raw["notificacoes"].get("ativo", False)),
        ),
        worker=WorkerConfig(
            max_retries_por_job=int(app_raw["worker"].get("max_retries_por_job", 3)),
            extensoes_aceitas=tuple(str(ext).lower() for ext in app_raw["worker"].get("extensoes_aceitas", [])),
        ),
        llm_modes=dict(llm_raw.get("modos", {})),
        llm_prompts=dict(llm_raw.get("prompts", {})),
        voice_profiles=dict(voices_raw.get("vozes", {})),
    )
    settings.ensure_directories()
    return settings
