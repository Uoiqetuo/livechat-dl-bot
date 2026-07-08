import asyncio
import logging
import discord
from uuid import UUID, uuid4
from typing import Any



from app.core.worker import Worker
from app.models.job import Job
from app.models.status_view import StatusView

logger = logging.getLogger(__name__)


class JobManager:
    def __init__(self, workers: int = 3):
        self.jobs: dict[UUID, Job] = {}
        self.queue = asyncio.Queue()
        self.workers = [Worker() for _ in range(workers)]

    async def worker_loop(self, worker: Worker):
        while True:
            job = await self.queue.get()
            try:
                await worker.execute(job, self.update_status_msg)
            except Exception:
                logger.exception(f"Job {job.id} failed")
            finally:
                self.jobs.pop(job.id, None)
                self.queue.task_done()

    async def create_job(
        self, url: str, opts: dict[str, Any], message: discord.Message
    ) -> UUID:
        status_view = await StatusView.create(message, lambda: self.cancel_job(job.id))

        job = Job(id=uuid4(), url=url, opts=opts, view=status_view)

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

        job.view.title = f"任務狀態: {job.status.value.capitalize()}"
        await job.view.submit()

    async def start(self):
        logger.info(f"JobManager started with {len(self.workers)} workers.")
        tasks = [
            asyncio.create_task(self.worker_loop(worker)) for worker in self.workers
        ]

        await asyncio.gather(*tasks)


job_manager_instance = JobManager(workers=3)
