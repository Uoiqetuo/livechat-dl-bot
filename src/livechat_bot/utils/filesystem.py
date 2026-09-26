import shutil
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def safe_file_component(value: str) -> str:
    """Keep externally supplied identifiers from becoming path components."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", value)
    return cleaned.strip("._") or "unknown"


def create_job_directory(data_dir: Path, job_id: str | None = None, now: datetime | None = None) -> Path:
    now = now or datetime.now()
    identifier = job_id or uuid4().hex
    path = Path(data_dir) / "jobs" / now.strftime("%Y%m%d") / identifier
    path.mkdir(parents=True, exist_ok=True)
    return path


def has_minimum_free_space(path: Path, minimum_gb: float) -> bool:
    return shutil.disk_usage(path).free >= int(minimum_gb * 1024**3)
