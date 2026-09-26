from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..enums import JobStatus


@dataclass(slots=True)
class DownloadJob:
    id: str
    youtube_url: str
    video_id: str | None
    title: str | None
    channel_name: str | None
    channel_url: str | None
    thumbnail_url: str | None
    scheduled_start: datetime | None
    guild_id: int
    channel_id: int
    message_id: int
    user_id: int
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    output_dir: Path
    chat_file: Path | None = None
    archive_file: Path | None = None
    error: str | None = None
    cookies_file: Path | None = None

    def transition(self, new_status: JobStatus) -> None:
        allowed = {
            JobStatus.PENDING: {JobStatus.RESOLVING, JobStatus.CANCELLED, JobStatus.FAILED},
            JobStatus.RESOLVING: {JobStatus.RECORDING, JobStatus.CANCELLED, JobStatus.FAILED},
            JobStatus.RECORDING: {JobStatus.COMPRESSING, JobStatus.CANCELLED, JobStatus.FAILED},
            JobStatus.COMPRESSING: {JobStatus.UPLOADING, JobStatus.FAILED},
            JobStatus.UPLOADING: {JobStatus.COMPLETED, JobStatus.FAILED},
            JobStatus.COMPLETED: set(),
            JobStatus.FAILED: set(),
            JobStatus.CANCELLED: set(),
        }
        if new_status == self.status:
            return
        if new_status not in allowed[self.status]:
            raise ValueError(f"invalid job transition {self.status.value} -> {new_status.value}")
        self.status = new_status

    def mark_started(self) -> None:
        self.started_at = self.started_at or datetime.now(timezone.utc)

    def mark_finished(self) -> None:
        self.finished_at = datetime.now(timezone.utc)
