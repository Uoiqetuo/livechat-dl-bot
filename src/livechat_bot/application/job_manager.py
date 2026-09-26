import asyncio
from typing import Any

from ..domain.enums import JobStatus
from ..domain.models import DownloadJob
from .download_service import JobAlreadyRunning


class JobManager:
    def __init__(self, download_service: Any, repository: Any, max_concurrent: int = 5):
        self.download_service = download_service
        self.repository = repository
        self.semaphore = asyncio.Semaphore(max(1, max_concurrent))
        self.tasks: dict[str, asyncio.Task] = {}
        self.cancel_events: dict[str, asyncio.Event] = {}
        self.accepting = True

    async def submit(self, job: DownloadJob) -> None:
        if not self.accepting:
            raise RuntimeError("job manager is shutting down")
        if job.video_id:
            duplicate = await self.repository.find_active_by_video_id(job.video_id)
            if duplicate and duplicate.id != job.id:
                raise JobAlreadyRunning(duplicate)
        await self.repository.create(job)
        await self.submit_existing(job)

    async def submit_existing(self, job: DownloadJob) -> None:
        """Schedule a job that has already been persisted (used by Discord)."""
        if not self.accepting:
            raise RuntimeError("job manager is shutting down")
        if job.id in self.tasks:
            return
        if job.video_id:
            duplicate = await self.repository.find_active_by_video_id(job.video_id)
            if duplicate and duplicate.id != job.id:
                raise JobAlreadyRunning(duplicate)
        event = asyncio.Event()
        self.cancel_events[job.id] = event
        task = asyncio.create_task(self._run(job, event), name=f"download-{job.id}")
        self.tasks[job.id] = task
        task.add_done_callback(lambda _: self._forget(job.id))

    async def _run(self, job: DownloadJob, event: asyncio.Event) -> None:
        async with self.semaphore:
            await self.download_service.run(job, event)

    def _forget(self, job_id: str) -> None:
        self.tasks.pop(job_id, None)
        self.cancel_events.pop(job_id, None)

    async def cancel(self, job_id: str) -> bool:
        job = await self.repository.get(job_id)
        if not job or not job.status.cancellable:
            return False
        event = self.cancel_events.get(job_id)
        if event is None:
            # A queued task may not have entered the runtime map yet.
            return False
        event.set()
        return True

    def get_task(self, job_id: str) -> asyncio.Task | None:
        return self.tasks.get(job_id)

    async def shutdown(self, timeout: float = 30) -> None:
        self.accepting = False
        for event in self.cancel_events.values():
            event.set()
        if self.tasks:
            await asyncio.wait(self.tasks.values(), timeout=timeout)
