from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

_download_dir_value = os.getenv("DOWNLOAD_DIR", "./downloads")
DOWNLOAD_DIR = Path(_download_dir_value).expanduser()
if not DOWNLOAD_DIR.is_absolute():
    DOWNLOAD_DIR = (PROJECT_ROOT / DOWNLOAD_DIR).resolve()

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


UPLOAD_TO_DISCORD = _env_flag("UPLOAD_TO_DISCORD", False)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()

COOKIES_PATH = os.getenv("COOKIES_PATH", "./cookies/cookies.txt")
