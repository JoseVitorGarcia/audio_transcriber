# Build do aplicativo Windows

O build é feito pelo GitHub Actions (`.github/workflows/build-windows.yml`) em `windows-latest`. Não é necessário ter Windows localmente.

## Disparar um build

**Manual (teste):** GitHub → aba *Actions* → *Build Windows* → *Run workflow*. Ao terminar, baixe o instalador em *Artifacts* (`TranscritorDeAudio-Setup`). A versão fica `0.0.0-dev`.

**Release:**

```bash
git tag v1.0.0
git push origin v1.0.0
```

O instalador `TranscritorDeAudio-Setup-1.0.0.exe` é anexado à Release da tag.

## Etapas do workflow

| Etapa | O que faz |
|-------|-----------|
| Instalar dependências | `requirements-windows.txt` + PyInstaller |
| Baixar modelo | `snapshot_download("Systran/faster-whisper-medium")` em `models/medium` (só `config.json`, `model.bin`, `tokenizer.json`, `vocabulary.*`) |
| Baixar ffmpeg | Build estático da BtbN; copia só o `ffmpeg.exe` para `ffmpeg/` |
| PyInstaller | `--windowed`, ícone, `--collect-all` de `faster_whisper`, `ctranslate2` e `onnxruntime`, e `--add-data` de `assets`, `ffmpeg` e `models` |
| Inno Setup | `installer/setup.iss` com `/DAppVersion=<versão da tag>` |
| Upload | Artifact (sem compressão extra) e, em tags, Release |

## Tamanho e limites

O modelo `medium` tem ~1,5 GB e comprime pouco, então o instalador fica em torno de 1,6 GB. O limite por arquivo em uma Release do GitHub é 2 GB. Se passar disso:

- troque para o modelo `small` (~480 MB) em `src/engine.py`, `app/window.py` e no passo de download do workflow; ou
- distribua o instalador apenas pelo *Artifact* do Actions.

## Ajustar

- **Nome, versão e atalhos do instalador:** `installer/setup.iss`.
- **Ícone:** `assets/make_icon.py` (regenera `icon.ico` e `icon.png`; commite os dois).
- **Modelo:** repositório e pasta no passo *Baixar modelo* e `load_model("medium")`.

## Solução de problemas

- **Falha no PyInstaller por módulo ausente:** adicione `--collect-all <módulo>` (ou `--hidden-import`) no passo *Empacotar*.
- **App abre e fecha sem mensagem:** gere um build temporário sem `--windowed` para ver o erro no console.
- **`Falha ao carregar o modelo`:** o `model.bin` não entrou em `models/medium`; verifique o passo de download.
- **Transcrição sem áudio/erro de ffmpeg:** confirme que `ffmpeg/ffmpeg.exe` existe após o passo *Baixar ffmpeg*.
- **Antivírus/SmartScreen avisando:** o instalador não é assinado digitalmente; é preciso um certificado de assinatura de código para remover o aviso.
