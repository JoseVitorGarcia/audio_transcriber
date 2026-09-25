import os
import redis

r = redis.Redis(host="redis", port=6379, decode_responses=True)

INPUT_DIR = "audios"
OUTPUT_DIR = "transcricoes"

SUPPORTED_FORMATS = (".mp3", ".wav", ".m4a", ".flac", ".ogg")

files = [
    f for f in os.listdir(INPUT_DIR)
    if f.lower().endswith(SUPPORTED_FORMATS)
]

for file in files:
    output_file = os.path.splitext(file)[0] + ".txt"
    output_path = os.path.join(OUTPUT_DIR, output_file)

    if os.path.exists(output_path):
        print(f"[SKIP] {file}")
        continue

    r.lpush("audio_queue", file)
    print(f"[ENVIADO] {file}")