# Audio Transcriber

Transcrição automática de áudios em português com [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (modelo `medium`, CPU, `int8`). O projeto tem duas formas de uso:

| Modo | Para quem | Como roda |
|------|-----------|-----------|
| **Aplicativo Windows** | Usuários finais | Instalador `.exe`, interface gráfica, 100% offline |
| **Fila com Docker** | Processamento em lote | Producer + workers + Redis |

Documentação detalhada: [docs/ARQUITETURA.md](docs/ARQUITETURA.md) e [docs/BUILD-WINDOWS.md](docs/BUILD-WINDOWS.md).

## Estrutura

```
├── app/
│   └── window.py            # interface PySide6 (janela, fila, thread de trabalho)
├── src/
│   ├── engine.py            # carga do modelo e transcrição de um arquivo (usado pelo app)
│   ├── paths.py             # localiza modelo e ffmpeg (dev, Docker ou PyInstaller)
│   ├── converter.py         # conversão para WAV 16 kHz mono via ffmpeg
│   └── transcriber.py       # processamento sequencial de uma pasta (usado por main.py)
├── assets/
│   ├── make_icon.py         # gera icon.ico / icon.png
│   ├── icon.ico
│   └── icon.png
├── installer/setup.iss      # script do instalador (Inno Setup)
├── .github/workflows/build-windows.yml
├── transcriber_app.py       # ponto de entrada do aplicativo Windows
├── main.py                  # CLI sem fila
├── producer.py / worker.py  # modo com fila (Redis)
├── Dockerfile / docker-compose.yml
├── requirements.txt         # modo Docker / CLI
└── requirements-windows.txt # aplicativo Windows
```

Pastas ignoradas pelo git: `audios/`, `transcricoes/`, `temp/`, `models/`, `dist/`, `build/`, `dist-installer/`, `ffmpeg/`, além de `*.zip`, `.claude/` e `.env*`.

---

## Aplicativo para Windows

Aplicativo desktop que funciona **sem internet**: o modelo Whisper `medium` e o ffmpeg vão embutidos no instalador.

### Como o usuário usa

1. Instalar com o `TranscritorDeAudio-Setup-<versão>.exe` (atalhos no menu Iniciar e na área de trabalho).
2. Clicar em **Adicionar áudios...** ou arrastar arquivos para a lista.
3. Acompanhar o status e o progresso de cada arquivo (na fila, transcrevendo, concluído, erro).
4. Selecionar um arquivo concluído para ver o texto e usar **Copiar texto** ou **Baixar .txt**.
5. **Limpar concluídos** remove da lista os arquivos já processados.

Formatos aceitos: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.mp4`, `.aac`, `.wma`, `.opus`.

Os arquivos são processados um por vez. Se o usuário fechar a janela durante uma transcrição, o app pede confirmação e cancela o trabalho em andamento.

**Desempenho de referência** (CPU, `int8`): num i7-13500 com 16 GB de RAM, a estimativa é de 1x a 2x a duração do áudio. No Linux, um áudio curto de WhatsApp levou cerca de 39 s. A primeira transcrição inclui alguns segundos para carregar o modelo.

### Gerar o instalador (GitHub Actions)

O workflow `build-windows.yml` roda em `windows-latest`:

1. Instala Python 3.11 e as dependências de `requirements-windows.txt`.
2. Baixa o modelo `Systran/faster-whisper-medium` para `models/medium`.
3. Baixa o ffmpeg (build estático) para `ffmpeg/ffmpeg.exe`.
4. Empacota com PyInstaller (modo `onedir`, sem console), incluindo ícone, ffmpeg e modelo.
5. Gera o instalador com Inno Setup.
6. Publica o `.exe` como *artifact* e, em tags `v*`, também em *Releases*.

Como disparar:

- **Manual:** aba *Actions* → *Build Windows* → *Run workflow*; o instalador fica em *Artifacts*.
- **Release:** `git tag v1.0.0 && git push origin v1.0.0`.

Passo a passo completo e solução de problemas em [docs/BUILD-WINDOWS.md](docs/BUILD-WINDOWS.md).

### Rodar a interface em desenvolvimento

```bash
pip install -r requirements-windows.txt
# coloque o modelo em models/medium (config.json, model.bin, tokenizer.json, vocabulary.*)
# e tenha o ffmpeg no PATH (ou em ffmpeg/ffmpeg[.exe])
python transcriber_app.py
```

### Ícone

`assets/icon.ico` (16 a 256 px) mostra uma onda sonora sobre linhas de texto, em azul e branco. Para alterá-lo, edite `assets/make_icon.py` e rode `python assets/make_icon.py` (requer Pillow).

---

## Modo em lote com Docker (fila Redis)

1. `producer.py` lê `audios/` e envia para a fila `audio_queue` todo arquivo que ainda não tem `.txt` em `transcricoes/`.
2. `worker.py` consome a fila, converte para WAV 16 kHz mono, transcreve e grava `transcricoes/<nome>.txt`.
3. Cada arquivo tem um lock distribuído no Redis (5 min) e até 3 tentativas antes de falha definitiva.

Formatos do producer: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`.

```bash
# 1. coloque os áudios em ./audios
docker compose up -d redis
docker compose up --build --scale worker=2 worker

# 2. em outro terminal, enfileire os áudios
docker compose run --rm producer
```

Na primeira execução o modelo (~1,5 GB) é baixado para `./models`. Para reprocessar um áudio, apague o `.txt` correspondente e rode o producer de novo.

### CLI sem fila

```bash
python main.py --input audios --output transcricoes --temp temp --model medium
```

Requer `ffmpeg` e `pip install -r requirements.txt`. Também aceita `.mp4` e usa filtro VAD. O cache do modelo fica em `/models`, ou no diretório da variável de ambiente `MODELS_DIR`.

---

## Configuração

| Item | Onde | Valor |
|------|------|-------|
| Idioma | `src/engine.py`, `worker.py`, `src/transcriber.py` | `pt` |
| Modelo | `src/engine.py` (`load_model`), `worker.py` | `medium` |
| Dispositivo / precisão | idem | `cpu` / `int8` |
| Threads de CPU (app) | `src/engine.py` | `max(4, núcleos - 2)` |
| Cache do modelo (Docker/CLI) | variável `MODELS_DIR` | `/models` |
| Host do Redis | `producer.py`, `worker.py` | `redis` |
| Timeout do ffmpeg | `src/converter.py` | 600 s |

Para trocar o modelo no aplicativo Windows, altere `medium` em `src/engine.py`/`app/window.py` e o repositório baixado no workflow (por exemplo `Systran/faster-whisper-small`, ~480 MB, mais rápido e menos preciso).

## Solução de problemas

- **`Nenhuma fala detectada no áudio`**: o filtro VAD não encontrou fala (áudio mudo ou só ruído).
- **`Falha ao carregar o modelo`** (app): a pasta `models/medium` não foi empacotada; confira o passo de download do modelo no workflow.
- **ffmpeg não encontrado** (dev): instale o ffmpeg e coloque-o no PATH.
- **Docker: worker não processa**: confirme que o Redis está de pé e que o producer enviou os arquivos (`[ENVIADO]` nos logs).
