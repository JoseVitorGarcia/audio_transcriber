import os
import shutil
import tempfile
import uuid
from typing import Callable

from faster_whisper import WhisperModel

from .converter import convert_to_wav
from .paths import bundled_model_dir


def load_model(name: str = "medium") -> WhisperModel:
    threads = max(4, (os.cpu_count() or 4) - 2)
    local = bundled_model_dir(name)
    if local:
        return WhisperModel(
            str(local),
            device="cpu",
            compute_type="int8",
            cpu_threads=threads,
            local_files_only=True,
        )
    return WhisperModel(
        name,
        device="cpu",
        compute_type="int8",
        cpu_threads=threads,
        download_root=os.environ.get("MODELS_DIR", "/models"),
    )


def transcribe_file(
    model: WhisperModel,
    input_path: str,
    on_progress: Callable[[float], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> str:
    work_dir = os.path.join(tempfile.gettempdir(), "audio-transcriber", uuid.uuid4().hex)
    try:
        wav_path = os.path.join(work_dir, "audio.wav")
        convert_to_wav(input_path, wav_path)

        segments, info = model.transcribe(wav_path, language="pt", vad_filter=True)

        parts = []
        for seg in segments:
            if should_cancel and should_cancel():
                raise InterruptedError("cancelado")
            parts.append(seg.text.strip())
            if on_progress and info.duration:
                on_progress(min(seg.end / info.duration, 1.0))

        text = " ".join(p for p in parts if p).strip()
        if not text:
            raise RuntimeError("Nenhuma fala detectada no áudio")
        return text
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
