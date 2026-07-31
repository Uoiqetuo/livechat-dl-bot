import asyncio
import logging
import discord
from uuid import UUID, uuid4
from typing import Any


from app.conf import confs
from app.core.cookie_file import CookieFile
from app.core.downloader import Downloader
from app.core.worker import Worker
from app.models.job import Job
from app.models.status_view import StatusView
from app.runtime_config import DOWNLOAD_DIR, COOKIES_PATH

logger = logging.getLogger(__name__)


class JobManager:
    def __init__(self, workers: int = 3):
        self.jobs: dict[UUID, Job] = {}
        self.queue = asyncio.Queue()
        self.workers = [Worker() for _ in range(workers)]
        self.metadata_downloader = Downloader()

    async def worker_loop(self, worker: Worker):
        while True:
            job = await self.queue.get()
            try:
                await worker.execute(job, self.update_status_msg)
            except Exception:
                logger.exception(f"Job {job.id} failed")
            finally:
                job.cleanup()
                self.jobs.pop(job.id, None)
                self.queue.task_done()

    async def create_job(
        self,
        url: str,
        message: discord.Message,
        use_cookie: bool = False,
    ) -> UUID:
        opts: dict[str, Any] = confs.get("default", {}) | confs.get("chat", {})

        # 設定下載路徑
        paths = dict(opts.get("paths", {}))
        paths["home"] = str(DOWNLOAD_DIR)
        opts["paths"] = paths

        cookie = CookieFile(COOKIES_PATH) if use_cookie else None
        if cookie:
            opts["cookiefile"] = cookie.path

        metadata = await asyncio.to_thread(
            self.metadata_downloader.extract_metadata, url, opts
        )

        job = Job(
            id=uuid4(),
            url=url,
            opts=opts,
            view=None,
            cookie=cookie,
            video_title=metadata.get("title"),
            video_url=metadata.get("webpage_url") or url,
            channel_name=metadata.get("uploader") or metadata.get("channel"),
            channel_url=metadata.get("uploader_url") or metadata.get("channel_url"),
            planned_start_timestamp=(
                metadata.get("release_timestamp") or metadata.get("timestamp")
            ),
            release_timestamp=metadata.get("release_timestamp"),
            duration=metadata.get("duration"),
            live_status=metadata.get("live_status"),
            extractor_key=metadata.get("extractor_key"),
            extractor=metadata.get("extractor"),
            video_id=metadata.get("id"),
            thumbnail_url=metadata.get("thumbnail"),
        )

        status_view = await StatusView.create(
            message, lambda: self.cancel_job(job.id), job
        )
        job.view = status_view

        self.jobs[job.id] = job

        await self.queue.put(job)

        return job.id

    async def cancel_job(self, job_id: UUID):
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"No job found for job ID: {job_id}")

        job.canceled = True

    async def update_status_msg(self, job_id: UUID):
        job = self.jobs.get(job_id)
        if not job or not job.view:
            raise ValueError(f"No job or view found for job ID: {job_id}")

        await job.view.submit()

    async def start(self):
        logger.info(f"JobManager started with {len(self.workers)} workers.")
        tasks = [
            asyncio.create_task(self.worker_loop(worker)) for worker in self.workers
        ]

        await asyncio.gather(*tasks)


job_manager_instance = JobManager(workers=3)
