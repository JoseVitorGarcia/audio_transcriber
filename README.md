# Audio Transcriber

Transcrição automática de áudios em português usando [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (modelo `medium`, CPU, `int8`). Os áudios são enfileirados no Redis por um *producer* e processados em paralelo por um ou mais *workers*.

## Como funciona

1. `producer.py` lê a pasta `audios/` e envia para a fila `audio_queue` (Redis) todo arquivo que ainda não tem `.txt` correspondente em `transcricoes/`.
2. `worker.py` consome a fila, converte o áudio para WAV 16 kHz mono com `ffmpeg` (`src/converter.py`), transcreve com faster-whisper e grava `transcricoes/<nome>.txt`.
3. Cada arquivo tem um lock distribuído no Redis (5 min) e até 3 tentativas antes de ser marcado como falha definitiva.

Formatos aceitos pelo producer: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`.

## Estrutura

```
├── audios/            # entrada (ignorado pelo git)
├── transcricoes/      # saída .txt (ignorado pelo git)
├── temp/              # WAVs temporários (ignorado pelo git)
├── models/            # cache do modelo Whisper (ignorado pelo git)
├── src/
│   ├── converter.py   # conversão via ffmpeg
│   └── transcriber.py # processamento sequencial de um diretório
├── producer.py        # enfileira os áudios
├── worker.py          # consome a fila e transcreve
├── main.py            # modo sem fila (CLI)
├── Dockerfile
└── docker-compose.yml
```

## Uso com Docker (recomendado)

Pré-requisito: Docker e Docker Compose.

```bash
# 1. coloque os áudios em ./audios
# 2. suba o Redis e os workers (escale conforme a CPU disponível)
docker compose up -d redis
docker compose up --build --scale worker=2 worker

# 3. em outro terminal, enfileire os áudios
docker compose run --rm producer
```

As transcrições aparecem em `./transcricoes`. Na primeira execução o modelo (~1,5 GB) é baixado para `./models`.

Para reprocessar um áudio, apague o `.txt` correspondente e rode o producer novamente.

## Modo sem fila

`main.py` processa um diretório de forma sequencial, sem Redis:

```bash
python main.py --input audios --output transcricoes --temp temp --model medium
```

Requer `ffmpeg` instalado e `pip install -r requirements.txt`. Esse modo também aceita `.mp4` e usa filtro VAD. O caminho do cache do modelo está fixo em `/models`, então ele é pensado para rodar dentro do container.

## Configuração

O idioma (`pt`), o modelo (`medium`) e o dispositivo (`cpu`, `int8`) estão definidos diretamente em `worker.py`. O host do Redis é `redis` (nome do serviço no compose).

## Aplicativo para Windows

Aplicativo desktop (PySide6) que funciona **100% offline**: o modelo Whisper `medium` e o ffmpeg vão embutidos no instalador. O usuário adiciona ou arrasta áudios, acompanha o progresso e, para cada arquivo, copia o texto ou baixa o `.txt`.

- Código: `transcriber_app.py` (entrada), `app/window.py` (interface) e `src/engine.py` (transcrição).
- Ícone: `assets/icon.ico`, gerado por `python assets/make_icon.py`.
- Build: o workflow `.github/workflows/build-windows.yml` roda em `windows-latest`, baixa o modelo e o ffmpeg, empacota com PyInstaller e gera o instalador com Inno Setup (`installer/setup.iss`).
  - Manual: aba *Actions* → *Build Windows* → *Run workflow* (o instalador fica em *Artifacts*).
  - Release: `git tag v1.0.0 && git push origin v1.0.0` publica o `Setup.exe` na aba *Releases*.

Para rodar a interface em desenvolvimento: `pip install -r requirements-windows.txt && python transcriber_app.py` (com o modelo em `models/medium` e o ffmpeg no PATH).
