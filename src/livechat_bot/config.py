import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Config:
    discord_token: str
    data_dir: Path
    max_concurrent_jobs: int = 5
    min_free_disk_gb: float = 5
    discord_max_file_size: int | None = None
    discord_upload_safety_margin: int = 1024
    discord_upload_retry_count: int = 3
    discord_ui_timezone: str = "Asia/Taipei"
    shutdown_timeout_seconds: float = 30
    command_prefix: str = "!"
    cookies_file: Path = Path("./cookies/cookies.txt")

    @classmethod
    def load(cls, env_file: str | Path | None = ".env") -> "Config":
        if env_file:
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                pass
        raw_limit = os.getenv("DISCORD_MAX_FILE_SIZE", "").strip()
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            data_dir=Path(os.getenv("DATA_DIR", "./data")),
            cookies_file=Path(os.getenv("COOKIES_FILE", "./cookies/cookies.txt")),
            max_concurrent_jobs=int(os.getenv("MAX_CONCURRENT_JOBS", "5")),
            min_free_disk_gb=float(os.getenv("MIN_FREE_DISK_GB", "5")),
            discord_max_file_size=int(raw_limit) if raw_limit else None,
            discord_upload_safety_margin=int(os.getenv("DISCORD_UPLOAD_SAFETY_MARGIN", "1024")),
            discord_upload_retry_count=int(os.getenv("DISCORD_UPLOAD_RETRY_COUNT", "3")),
            discord_ui_timezone=os.getenv("DISCORD_UI_TIMEZONE", "Asia/Taipei"),
            shutdown_timeout_seconds=float(os.getenv("SHUTDOWN_TIMEOUT_SECONDS", "30")),
            command_prefix=os.getenv("COMMAND_PREFIX", "!"),
        )
