import os
import redis
import uuid
import shutil
from faster_whisper import WhisperModel
from src.converter import convert_to_wav

r = redis.Redis(host="redis", port=6379, decode_responses=True)

INPUT_DIR = "audios"
OUTPUT_DIR = "transcricoes"
TEMP_DIR = "temp"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

print("[INFO] Carregando modelo (faster-whisper medium)...")
model = WhisperModel(
    "medium",
    device="cpu",
    compute_type="int8",
    download_root="/models"
)

WORKER_ID = str(uuid.uuid4())[:8]
print(f"[WORKER] ID: {WORKER_ID}")

while True:
    _, file = r.brpop("audio_queue")

    lock_key = f"lock:{file}"
    retry_key = f"retry:{file}"

    # 🔒 lock distribuído
    if not r.set(lock_key, WORKER_ID, nx=True, ex=300):
        print(f"[SKIP LOCK] {file}")
        continue

    worker_temp_dir = None

    try:
        print(f"[PROCESSANDO] {file}")

        input_path = os.path.join(INPUT_DIR, file)

        if not os.path.exists(input_path):
            raise RuntimeError("Arquivo não existe")

        output_file = os.path.splitext(file)[0] + ".txt"
        output_path = os.path.join(OUTPUT_DIR, output_file)

        # evita reprocessar
        if os.path.exists(output_path):
            print(f"[SKIP] {file}")
            continue

        # diretório isolado
        worker_temp_dir = os.path.join(TEMP_DIR, str(uuid.uuid4()))
        os.makedirs(worker_temp_dir, exist_ok=True)

        wav_path = os.path.join(worker_temp_dir, "audio.wav")

        convert_to_wav(input_path, wav_path)

        if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 5000:
            raise RuntimeError("WAV inválido")

        # 🚀 faster-whisper
        segments, _ = model.transcribe(
            wav_path,
            language="pt"
        )

        text = " ".join(seg.text for seg in segments).strip()

        if not text:
            raise RuntimeError("Transcrição vazia")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"[OK] {file}")

        r.delete(retry_key)

    except Exception as e:
        print(f"[ERRO] {file} -> {e}")

        retries = r.incr(retry_key)

        if retries < 3:
            print(f"[RETRY {retries}] {file}")
            r.lpush("audio_queue", file)
        else:
            print(f"[FALHA DEFINITIVA] {file}")

    finally:
        r.delete(lock_key)

        if worker_temp_dir and os.path.exists(worker_temp_dir):
            shutil.rmtree(worker_temp_dir, ignore_errors=True)