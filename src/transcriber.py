import os
import time
import uuid
import shutil
from tqdm import tqdm
from faster_whisper import WhisperModel
from .converter import convert_to_wav

SUPPORTED_FORMATS = (".mp4",".mp3", ".wav", ".m4a", ".flac", ".ogg")


class AudioTranscriber:
    def __init__(self, model_name="medium"):
        self.model_name = model_name

    def process_directory(self, input_dir, output_dir, temp_dir):
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        files = [
            f for f in os.listdir(input_dir)
            if f.lower().endswith(SUPPORTED_FORMATS)
        ]

        print(f"[DEBUG] Total de arquivos: {len(files)}")

        if not files:
            raise RuntimeError(f"Nenhum arquivo encontrado em '{input_dir}'")

        print("[INFO] Carregando modelo (faster-whisper)...")

        model = WhisperModel(
            self.model_name,
            device="cpu",
            compute_type="int8",
            download_root="/models"
        )

        start_time = time.time()
        results = []

        for file in tqdm(files, desc="Transcrevendo", unit="arquivo"):
            worker_temp_dir = None

            try:
                input_path = os.path.join(input_dir, file)

                output_file = os.path.splitext(file)[0] + ".txt"
                output_path = os.path.join(output_dir, output_file)

                if os.path.exists(output_path):
                    results.append(True)
                    continue

                worker_temp_dir = os.path.join(temp_dir, str(uuid.uuid4()))
                os.makedirs(worker_temp_dir, exist_ok=True)

                wav_path = os.path.join(worker_temp_dir, "audio.wav")

                convert_to_wav(input_path, wav_path)

                if not os.path.exists(wav_path):
                    raise RuntimeError("Falha ao converter áudio")

                segments, _ = model.transcribe(
                    wav_path,
                    language="pt",
                    vad_filter=True
                )

                segments = list(segments)

                text = "".join(seg.text for seg in segments).strip()

                if not text:
                    results.append(False)
                    continue

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text)

                results.append(True)

            except Exception as e:
                print(f"[ERRO] {file} -> {e}")
                results.append(False)

            finally:
                if worker_temp_dir and os.path.exists(worker_temp_dir):
                    shutil.rmtree(worker_temp_dir, ignore_errors=True)

        elapsed = time.time() - start_time

        print("\n📊 RESUMO FINAL")
        print(f"Tempo total: {elapsed:.2f}s")
        print(f"Sucesso: {sum(results)}")
        print(f"Erros: {len(results) - sum(results)}")