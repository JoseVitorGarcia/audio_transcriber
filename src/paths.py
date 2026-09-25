import os
import sys
from pathlib import Path


def resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def ffmpeg_path() -> str:
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    bundled = resource_dir() / "ffmpeg" / exe
    return str(bundled) if bundled.exists() else "ffmpeg"


def bundled_model_dir(name: str = "medium") -> Path | None:
    path = resource_dir() / "models" / name
    return path if (path / "model.bin").exists() else None
