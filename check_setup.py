from __future__ import annotations

import importlib
from pathlib import Path
import sys
import tempfile

import requests

VERDE = "\033[92m"
VERMELHO = "\033[91m"
AMARELO = "\033[93m"
RESET = "\033[0m"
NEGRITO = "\033[1m"

results: list[tuple[str, bool]] = []


def ok(name: str, detail: str = "") -> None:
    message = f"{VERDE}OK{RESET}  {name}"
    if detail:
        message += f" {AMARELO}({detail}){RESET}"
    print(message)
    results.append((name, True))


def fail(name: str, detail: str = "") -> None:
    message = f"{VERMELHO}FALHA{RESET}  {name}"
    if detail:
        message += f" - {detail}"
    print(message)
    results.append((name, False))


def warn(name: str, detail: str = "") -> None:
    message = f"{AMARELO}AVISO{RESET}  {name}"
    if detail:
        message += f" - {detail}"
    print(message)


print(f"\n{NEGRITO}=== Check Setup ==={RESET}\n")

print(f"{NEGRITO}[ Python ]{RESET}")
version = sys.version_info
if version.major == 3 and version.minor >= 11:
    ok("Python", f"{version.major}.{version.minor}.{version.micro}")
else:
    fail("Python", f"versao atual {version.major}.{version.minor}.{version.micro}; requer 3.11+")

print(f"\n{NEGRITO}[ Dependencias Python ]{RESET}")
imports = {
    "yaml": "pyyaml",
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "docx": "python-docx",
    "ebooklib": "ebooklib",
    "fitz": "pymupdf",
    "pymupdf4llm": "pymupdf4llm",
    "pytesseract": "pytesseract",
    "piper": "piper-tts",
}
import_status: dict[str, bool] = {}
for module_name, package_name in imports.items():
    try:
        importlib.import_module(module_name)
        ok(module_name)
        import_status[module_name] = True
    except Exception:
        fail(module_name, f"pip install {package_name}")
        import_status[module_name] = False

settings = None
if import_status.get("yaml"):
    try:
        from app.core.config import load_settings

        settings = load_settings()
    except Exception as exc:
        fail("load_settings", str(exc))
else:
    fail("load_settings", "PyYAML ausente; configuracao nao pode ser carregada")

if settings is not None:
    print(f"\n{NEGRITO}[ Configuracao ]{RESET}")
    ok("Projeto", settings.project.name)
    ok("Base", str(settings.paths.base))
    if settings.paths.fonte_artigos is not None:
        if settings.paths.fonte_artigos.exists():
            ok("Fonte de artigos", str(settings.paths.fonte_artigos))
        else:
            warn("Fonte de artigos", f"pasta configurada nao encontrada: {settings.paths.fonte_artigos}")
    for directory in (
        settings.paths.entrada,
        settings.paths.processando,
        settings.paths.concluidos,
        settings.paths.falhas,
        settings.paths.saida_audio,
        settings.paths.saida_sync,
        settings.paths.temp,
        settings.paths.logs,
    ):
        if directory.exists():
            ok(f"Diretorio {directory.name}")
        else:
            fail(f"Diretorio {directory.name}", "nao existe")

    print(f"\n{NEGRITO}[ Escrita local ]{RESET}")
    for target in (settings.paths.temp, settings.paths.saida_sync):
        try:
            target.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix="check_", suffix=".tmp", dir=target, delete=False) as handle:
                temp_path = Path(handle.name)
            temp_path.unlink(missing_ok=True)
            ok(f"Escrita em {target}")
        except Exception as exc:
            fail(f"Escrita em {target}", str(exc))

    print(f"\n{NEGRITO}[ Tesseract ]{RESET}")
    if settings.tesseract.executavel.exists():
        ok("Executavel Tesseract", str(settings.tesseract.executavel))
    else:
        fail("Executavel Tesseract", str(settings.tesseract.executavel))

    print(f"\n{NEGRITO}[ LM Studio ]{RESET}")
    try:
        response = requests.get(f"{settings.llm.url_base}/models", timeout=5)
        response.raise_for_status()
        models = [item.get("id") for item in response.json().get("data", []) if item.get("id")]
        if models:
            ok("LM Studio server", ", ".join(models[:5]))
            if settings.llm.model and settings.llm.model not in models:
                warn("Modelo configurado", f"{settings.llm.model} nao apareceu em /models")
        else:
            fail("LM Studio server", "nenhum modelo retornado")
    except Exception as exc:
        fail("LM Studio server", str(exc))

    print(f"\n{NEGRITO}[ TTS ]{RESET}")
    if settings.tts.enabled:
        ok("TTS habilitado", f"provider atual: {settings.tts.provider}")
        if settings.tts.provider.lower() == "piper":
            data_dir = Path(str(settings.tts.settings.get("data_dir", "data/voices")))
            if not data_dir.is_absolute():
                data_dir = (settings.paths.base / data_dir).resolve()
            voice_name = str(settings.tts.settings.get("voice", "")).strip()
            voice_file = str(settings.tts.settings.get("voice_file", "")).strip()
            model_path = Path(voice_file) if voice_file else (data_dir / f"{voice_name}.onnx" if voice_name else data_dir)
            if not model_path.is_absolute():
                model_path = (data_dir / model_path).resolve()
            if model_path.exists():
                ok("Modelo Piper", str(model_path))
            else:
                fail("Modelo Piper", f"nao encontrado: {model_path}")
    else:
        ok("TTS desabilitado", "comportamento esperado para este v1")

    print(f"\n{NEGRITO}[ Notificacoes ]{RESET}")
    if settings.notifications.ativo:
        if settings.notifications.canal_ntfy:
            ok("ntfy configurado", settings.notifications.canal_ntfy)
        else:
            fail("ntfy configurado", "ativo=true mas canal_ntfy esta vazio")
    else:
        ok("ntfy desabilitado")

print(f"\n{NEGRITO}=== Resumo ==={RESET}")
approved = sum(1 for _, passed in results if passed)
failed = len(results) - approved
print(f"Verificacoes: {len(results)}")
print(f"{VERDE}Aprovadas: {approved}{RESET}")
if failed:
    print(f"{VERMELHO}Falhas: {failed}{RESET}")
    print(f"{AMARELO}Resolva as falhas antes de rodar o pipeline em producao.{RESET}")
else:
    print(f"{VERDE}Ambiente pronto para o v1 do pipeline.{RESET}")
