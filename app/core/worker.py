import logging
from typing import Callable, Awaitable
from uuid import UUID

from yt_dlp.utils import DownloadCancelled

from app.core.archiver import Archiver
from app.core.downloader import Downloader
from app.core.uploader import Uploader
from app.models.job import Job, JobStatus
from app.runtime_config import UPLOAD_TO_DISCORD

logger = logging.getLogger(__name__)

class Worker:
    def __init__(self):
        self.downloader = Downloader()
        self.archiver = Archiver()
        self.uploader = Uploader()

    async def execute(
        self, job: Job, update_status_msg: Callable[[UUID], Awaitable[None]]
    ):
        job.status = JobStatus.DOWNLOADING
        await update_status_msg(job.id)
        try:
            await self.downloader.download(job)
        except DownloadCancelled:
            job.status = JobStatus.CANCELED
            logger.info(f"下載取消: {job.url}")
            await update_status_msg(job.id)
            return

        job.status = JobStatus.ARCHIVING
        self.archiver.archive(
            job, split=True, split_size=10 * 1024 * 1024, cleanup=True
        )

        if UPLOAD_TO_DISCORD:
            job.status = JobStatus.UPLOADING
            await self.uploader.upload(job, cleanup=True)

        job.status = JobStatus.FINISHED
        if job.view:
            job.view.show_controls = False
        await update_status_msg(job.id)
        logger.info(f"任務完成: {job.url}, 檔案路徑: {job.archived_paths}")
