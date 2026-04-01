# Article to Audio

Pipeline local para Windows 11 que:

- extrai texto de PDF, TXT, MD, DOCX e EPUB
- usa LM Studio por API para limpar, traduzir/adaptar para PT-BR e gerar resumo
- publica um pacote final em pasta local sincronizada com Google Drive
- deixa a camada de TTS desacoplada e opcional ate a escolha do provider

## Comandos

```powershell
python -m app.cli.run --input data/entrada
python -m app.cli.retry --failed
python -m app.cli.status --last 20
python check_setup.py
```

## Configuracao

A configuracao principal fica em `config/app.yaml`.

Campos importantes:

- `llm.url_base`: endpoint do LM Studio, por exemplo `http://localhost:1234/v1`
- `llm.model`: nome do modelo ou vazio para resolver dinamicamente via `/models`
- `tts.enabled`: `false` por padrao
- `notificacoes.ativo`: ativa ou desativa `ntfy`
- `caminhos.saida_sync`: pasta local sincronizada com Google Drive

## Pacote final por documento

Cada job concluido publica uma pasta no destino sincronizado contendo:

- `texto_limpo.md`
- `resumo.md`
- `manifest.json`
- `job.log`
- artefatos de audio quando um provider TTS for implementado e habilitado
