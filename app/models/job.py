from attr import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import UUID

from app.core.cookie_file import CookieFile
from app.models.status_view import StatusView


class JobStatus(Enum):
    WAITING = "等待中"

    DOWNLOADING = "下載中"

    ARCHIVING = "封存中"

    UPLOADING = "上傳中"

    FINISHED = "已完成"

    CANCELED = "已取消"

    FAILED = "失敗"


@dataclass
class Job:
    id: UUID
    url: str
    opts: dict
    view: StatusView | None
    cookie: CookieFile | None = None
    status: JobStatus = JobStatus.WAITING
    canceled: bool = False
    downloaded_path: Path | None = None
    archived_paths: list[Path] | None = None
    video_title: str | None = None
    video_url: str | None = None
    channel_name: str | None = None
    channel_url: str | None = None
    planned_start_timestamp: int | None = None
    release_timestamp: int | None = None
    duration: int | float | None = None
    live_status: str | None = None
    extractor_key: str | None = None
    extractor: str | None = None
    recording_finished_at: datetime | None = None
    video_id: str | None = None
    thumbnail_url: str | None = None

    def cleanup(self):
        if self.cookie:
            self.cookie.cleanup()
