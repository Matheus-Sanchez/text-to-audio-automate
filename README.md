# Article to Audio

Pipeline local para Windows 11 que:

- extrai texto de PDF, TXT, MD, DOCX e EPUB
- usa LM Studio por API para limpar, traduzir/adaptar para PT-BR e gerar resumo
- copia artigos de uma pasta externa para a fila interna sem mover os originais
- gera audio local com Piper em PT-BR
- publica um pacote final com `.txt` e audio em uma pasta local

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
- `tts.enabled`: ativa ou desativa a geracao de audio
- `tts.settings.voice`: nome da voz Piper, por exemplo `pt_BR-faber-medium`
- `notificacoes.ativo`: ativa ou desativa `ntfy`
- `caminhos.saida_sync`: pasta local onde o pacote final e publicado

## Pacote final por documento

Cada job concluido publica uma pasta no destino sincronizado contendo:

- `texto_limpo.txt`
- `resumo.txt`
- `narracao.wav`
- `resumo.wav`
- `manifest.json`
- `job.log`
