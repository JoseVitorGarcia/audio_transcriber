# Arquitetura

## Visão geral

Todo o processamento de áudio passa pelo mesmo pipeline:

```
áudio (mp3/ogg/m4a/...) ──ffmpeg──▶ WAV 16 kHz mono normalizado ──faster-whisper──▶ texto (pt)
```

- **Conversão** (`src/converter.py`): `ffmpeg` gera `pcm_s16le`, 16 kHz, mono, com o filtro `dynaudnorm=f=200:g=15` para normalizar volume. Falha se o WAV gerado tiver menos de 5000 bytes. No Windows o ffmpeg é executado sem abrir janela de console (`CREATE_NO_WINDOW`).
- **Transcrição**: `WhisperModel` do faster-whisper, idioma `pt`, CPU, `int8`.

## Aplicativo Windows

```
transcriber_app.py ─▶ app.window.run()
                          │
              MainWindow (thread da UI)
                 │  sinais/slots
              Worker (QThread) ─▶ src.engine.load_model / transcribe_file
```

- **`app/window.py`**
  - `MainWindow`: lista de arquivos (com arrastar e soltar), painel de texto, botões de copiar e baixar, barra de progresso.
  - `Worker`: roda numa `QThread`, carrega o modelo uma vez por lote e processa os arquivos em sequência. Comunica-se com a UI apenas por sinais (`started`, `progress`, `finished_file`, `failed`, `all_done`).
  - Arquivos adicionados durante um processamento entram numa lista pendente e iniciam um novo lote quando o atual termina.
  - Ao fechar a janela com trabalho em andamento, o worker é cancelado (`cancel()`), e o cancelamento é verificado a cada segmento transcrito.
- **`src/engine.py`**
  - `load_model(name)`: usa o modelo embutido (`models/<name>` com `model.bin`) com `local_files_only=True`; se não existir, cai no modo Docker/CLI, com `download_root` em `MODELS_DIR` (padrão `/models`).
  - `transcribe_file(model, path, on_progress, should_cancel)`: converte, transcreve com `vad_filter=True`, calcula o progresso por `seg.end / info.duration` e limpa o diretório temporário (em `tempfile.gettempdir()`) ao final. Levanta erro se não houver fala.
- **`src/paths.py`**: `resource_dir()` aponta para `sys._MEIPASS` quando empacotado (PyInstaller) ou para a raiz do repositório em desenvolvimento. De lá saem `ffmpeg/ffmpeg(.exe)` e `models/<name>`; se o ffmpeg embutido não existir, usa o do `PATH`.

### Decisões

| Decisão | Motivo |
|---------|--------|
| Sem Redis/Docker no app | Usuários não técnicos; instalação simples e uso offline |
| Modelo `medium` embutido | Requisito de não acessar a internet durante o uso; melhor qualidade em português |
| Um arquivo por vez | Modelo em CPU já usa vários threads; evita estourar a RAM (16 GB) |
| PyInstaller `onedir` | Inicialização mais rápida que `onefile` (que descompactaria 1,5 GB a cada abertura) |
| Inno Setup | Instalador com atalhos e desinstalador, familiar para usuários finais |
| ffmpeg mantido (mesmo com PyAV) | Preserva a normalização de áudio já usada nos outros modos |

## Modo em lote (Docker)

```
producer.py ──LPUSH──▶ Redis (audio_queue) ──BRPOP──▶ worker.py (N réplicas)
```

- O producer ignora arquivos que já têm `.txt` de saída.
- O worker usa `SET lock:<arquivo> NX EX 300` para evitar processamento duplicado e `retry:<arquivo>` para contar tentativas (máx. 3, reenfileirando em caso de erro).
- Cada worker usa um diretório temporário isolado em `temp/<uuid>`, removido ao final.
