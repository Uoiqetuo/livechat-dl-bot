import asyncio
from pathlib import Path
from typing import Any


class UploadService:
    def __init__(self, uploader: Any, archive_service: Any, policy: Any,
                 retry_count: int = 3, safety_margin: int = 1024):
        self.uploader = uploader
        self.archive_service = archive_service
        self.policy = policy
        self.retry_count = max(1, retry_count)
        self.safety_margin = max(0, safety_margin)

    async def upload(self, job: Any, archive: Path) -> None:
        guild = getattr(self.uploader, "get_guild", lambda _: None)(job.guild_id)
        limit = self.policy.get_max_file_size(guild)
        max_part_size = max(1, limit - self.safety_margin)
        parts = await self.archive_service.split_archive(archive, max_part_size)
        succeeded = False
        try:
            last: Exception | None = None
            for attempt in range(self.retry_count):
                try:
                    await self.uploader.upload_to_job_message(job, parts)
                    last = None
                    succeeded = True
                    break
                except Exception as exc:
                    last = exc
                    if attempt + 1 < self.retry_count:
                        await asyncio.sleep(min(2 ** attempt, 8))
            if last:
                raise last
        finally:
            # Parts are disposable; the canonical archive is never removed.
            if succeeded:
                await self.archive_service.cleanup_parts(parts, archive)
