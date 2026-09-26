from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class StreamInfo:
    video_id: str
    video_url: str
    title: str
    channel_name: str | None = None
    channel_url: str | None = None
    thumbnail_url: str | None = None
    scheduled_start: datetime | None = None
    live_status: str | None = None
