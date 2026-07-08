from attr import dataclass
from enum import Enum
from pathlib import Path
from uuid import UUID

from app.models.status_view import StatusView


class JobStatus(Enum):
    PENDING = "pending"

    WAITING = "waiting"

    DOWNLOADING = "downloading"

    ARCHIVING = "archiving"

    UPLOADING = "uploading"

    FINISHED = "finished"

    CANCELED = "canceled"

    FAILED = "failed"


@dataclass
class Job:
    id: UUID
    url: str
    opts: dict
    view: StatusView
    status: JobStatus = JobStatus.PENDING
    canceled: bool = False
    downloaded_path: Path | None = None
    archived_paths: list[Path] | None = None
