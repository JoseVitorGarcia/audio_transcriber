import subprocess
import os

def convert_to_wav(input_path: str, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        "-af", "dynaudnorm=f=200:g=15,aresample=16000",
        output_path
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    if not os.path.exists(output_path):
        raise RuntimeError("WAV não gerado")

    size = os.path.getsize(output_path)
    if size < 5000:
        raise RuntimeError(f"WAV muito pequeno ({size})")

    return output_path