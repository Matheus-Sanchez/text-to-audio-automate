# Article to Audio

Pipeline local para Windows 11 que:

- extrai texto de PDF, TXT, MD, DOCX e EPUB
- usa LM Studio por API para limpar, traduzir/adaptar para PT-BR e gerar resumo
- copia artigos de uma pasta externa para a fila interna sem mover os originais
- publica um pacote final com arquivos `.txt` prontos para TTS em uma pasta local
- deixa a camada de TTS desacoplada e opcional ate a escolha do provider

## Comandos

```powershell
py -3.11 -m app.cli.run
py -3.11 -m app.cli.run --sync-from "C:\Users\matheus.sduda\Meu Drive\TCC (1)"
py -3.11 -m app.cli.retry --failed
py -3.11 -m app.cli.status --last 20
py -3.11 check_setup.py
```

## Configuracao

A configuracao principal fica em `config/app.yaml`.

Campos importantes:

- `llm.url_base`: endpoint do LM Studio, por exemplo `http://localhost:1234/v1`
- `llm.model`: nome do modelo ou vazio para resolver dinamicamente via `/models`
- `caminhos.fonte_artigos`: pasta externa com os PDFs originais; eles sao copiados para a fila do projeto
- `tts.enabled`: `false` por padrao
- `notificacoes.ativo`: ativa ou desativa `ntfy`
- `caminhos.saida_sync`: pasta local onde o pacote final e publicado

## Pacote final por documento

Cada job concluido publica uma pasta no destino sincronizado contendo:

- `texto_limpo.txt`
- `resumo.txt`
- `manifest.json`
- `job.log`
- artefatos de audio quando um provider TTS for implementado e habilitado
