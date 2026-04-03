from __future__ import annotations

from pathlib import Path
import textwrap


def write_config_bundle(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "data" / "entrada").mkdir(parents=True, exist_ok=True)
    (root / "data" / "processando").mkdir(parents=True, exist_ok=True)
    (root / "data" / "concluidos").mkdir(parents=True, exist_ok=True)
    (root / "data" / "falhas").mkdir(parents=True, exist_ok=True)
    (root / "data" / "saida_audio").mkdir(parents=True, exist_ok=True)
    (root / "data" / "saida_sync").mkdir(parents=True, exist_ok=True)
    (root / "data" / "temp").mkdir(parents=True, exist_ok=True)
    (root / "data" / "logs").mkdir(parents=True, exist_ok=True)
    (root / "db").mkdir(parents=True, exist_ok=True)
    (root / "config" / "app.yaml").write_text(
        textwrap.dedent(
            """
            projeto:
              nome: test_project
              versao: "0.1.0"
            caminhos:
              base: "."
              entrada: "data/entrada"
              fonte_artigos: ""
              processando: "data/processando"
              concluidos: "data/concluidos"
              falhas: "data/falhas"
              saida_audio: "data/saida_audio"
              saida_sync: "data/saida_sync"
              temp: "data/temp"
              logs: "data/logs"
            banco:
              caminho: "db/app.db"
            tesseract:
              executavel: "C:/Program Files/Tesseract-OCR/tesseract.exe"
              idioma: "por"
              confianca_minima: 70
              fallback_chars_minimos: 10
            llm:
              url_base: "http://localhost:1234/v1"
              model: ""
              api_key: "lm-studio"
              timeout_segundos: 30
              contexto_maximo: 4096
              chunk_chars: 300
              overlap_chars: 20
              temperatura_padrao: 0.2
            tts:
              enabled: false
              provider: "disabled"
              output_format: "mp3"
              settings: {}
            notificacoes:
              canal_ntfy: ""
              url_ntfy: "https://ntfy.sh"
              ativo: false
            worker:
              max_retries_por_job: 3
              extensoes_aceitas:
                - ".pdf"
                - ".txt"
                - ".md"
                - ".docx"
                - ".epub"
            """
        ).strip(),
        encoding="utf-8",
    )
    (root / "config" / "llm.yaml").write_text(
        textwrap.dedent(
            """
            modos:
              leitura_integral:
                temperatura: 0.2
                max_tokens: 512
              resumo:
                temperatura: 0.3
                max_tokens: 256
            prompts:
              sistema_base: |
                Sistema base de teste.
              leitura_integral: |
                Limpe o trecho.
              resumo: |
                Resuma o texto.
              resumo_parcial: |
                Resuma a parte.
              resumo_consolidado: |
                Consolide os resumos.
            """
        ).strip(),
        encoding="utf-8",
    )
    (root / "config" / "voices.yaml").write_text(
        "vozes:\n  padrao:\n    provider: disabled\n",
        encoding="utf-8",
    )
