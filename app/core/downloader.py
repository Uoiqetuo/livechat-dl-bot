import asyncio
import logging
import yt_dlp
from pathlib import Path
from typing import Any, cast

from yt_dlp.utils import DownloadCancelled
from app.models.job import Job

logger = logging.getLogger(__name__)


class Downloader:

    async def download(self, job: Job):
        await asyncio.to_thread(self._download, job=job)
        logger.info(f"下載完成: {job.downloaded_path}")

    def _download(self, job: Job):
        opts = dict(job.opts)
        hooks = list(opts.get("progress_hooks", []))
        hooks.append(lambda data: self._progress_hook(data, job))
        opts["progress_hooks"] = hooks

        with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
            ydl.download([job.url])

    def _progress_hook(self, _data: dict[str, Any], job: Job):
        if _data.get("status") == "finished":
            filename = _data.get("filepath") or _data.get("filename")
            if filename:
                job.downloaded_path = Path(cast(str, filename))
        if job.canceled:
            raise DownloadCancelled("Cancelled by user")