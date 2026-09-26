import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from ..domain.enums import JobStatus
from ..domain.models import DownloadJob
from ..utils.filesystem import safe_file_component
from .errors import JobAlreadyRunning, JobCancellationError

log = logging.getLogger(__name__)


class DuplicateJobError(JobAlreadyRunning):
    def __init__(self, job: DownloadJob):
        self.job = job
        super().__init__(job)


class DownloadService:
    def __init__(self, repository: Any, youtube: Any, archive_service: Any,
                 upload_service: Any, message_updater: Callable[[DownloadJob], Awaitable[None]] | None = None,
                 disk_checker: Callable[[], bool] | None = None):
        self.repository = repository
        self.youtube = youtube
        self.archive_service = archive_service
        self.upload_service = upload_service
        self.message_updater = message_updater
        self.disk_checker = disk_checker

    async def _save(self, job: DownloadJob, update_message: bool = False) -> None:
        await self.repository.update(job)
        if update_message and self.message_updater:
            try:
                await self.message_updater(job)
            except Exception:
                log.exception("job=%s message update failed", job.id)

    async def _status(self, job: DownloadJob, status: JobStatus,
                      update_message: bool = False) -> None:
        job.transition(status)
        await self._save(job, update_message=update_message)
        log.info("job=%s video=%s status=%s", job.id, job.video_id, status.value)

    async def _cancel(self, job: DownloadJob) -> None:
        if not job.status.terminal:
            job.transition(JobStatus.CANCELLED)
            await self._save(job, update_message=True)

    async def run(self, job: DownloadJob, cancel_event: Any) -> None:
        try:
            if cancel_event.is_set():
                await self._cancel(job)
                return
            if self.disk_checker and not self.disk_checker():
                job.error = "Insufficient free disk space"
                await self._status(job, JobStatus.FAILED, update_message=True)
                return
            await self._status(job, JobStatus.RESOLVING)
            if job.cookies_file:
                info = await self.youtube.get_stream_info(job.youtube_url, job.cookies_file)
            else:
                info = await self.youtube.get_stream_info(job.youtube_url)
            job.video_id, job.title, job.channel_name = info.video_id, info.title, info.channel_name
            job.channel_url, job.thumbnail_url = info.channel_url, info.thumbnail_url
            job.scheduled_start = info.scheduled_start
            claim = getattr(self.repository, "claim_video_id", None)
            duplicate = await claim(job.id, info.video_id) if claim is not None else None
            if claim is None:
                await self._save(job, update_message=False)
                duplicate = await self.repository.find_active_by_video_id(info.video_id)
            if duplicate and duplicate.id != job.id:
                raise DuplicateJobError(duplicate)
            await self._save(job)
            if cancel_event.is_set():
                await self._cancel(job)
                return
            await self._status(job, JobStatus.RECORDING, update_message=True)
            job.mark_started()
            await self._save(job, update_message=False)
            try:
                if job.cookies_file:
                    job.chat_file = await self.youtube.download_live_chat(
                        job.youtube_url, job.output_dir, cancel_event, job.cookies_file
                    )
                else:
                    job.chat_file = await self.youtube.download_live_chat(
                        job.youtube_url, job.output_dir, cancel_event
                    )
            except Exception:
                if cancel_event.is_set():
                    await self._cancel(job)
                    return
                raise
            job.mark_finished()
            await self._save(job, update_message=False)
            if cancel_event.is_set():
                await self._cancel(job)
                return
            await self._status(job, JobStatus.COMPRESSING)
            archive = job.output_dir / f"{safe_file_component(job.video_id)}.zip"
            job.archive_file = await self.archive_service.create_archive(job.chat_file, archive)
            await self._save(job)
            await self._status(job, JobStatus.UPLOADING)
            await self.upload_service.upload(job, job.archive_file)
            await self._status(job, JobStatus.COMPLETED, update_message=True)
        except JobAlreadyRunning as exc:
            job.error = str(exc)
            await self._status(job, JobStatus.FAILED, update_message=True)
            return
        except Exception as exc:
            if cancel_event.is_set() and job.status.cancellable:
                await self._cancel(job)
                return
            job.error = str(exc)[:1000]
            log.exception("job=%s video=%s status=%s failed", job.id, job.video_id, job.status.value)
            if not job.status.terminal:
                await self._status(job, JobStatus.FAILED, update_message=True)
        finally:
            self._remove_temporary_cookies(job)

    @staticmethod
    def _remove_temporary_cookies(job: DownloadJob) -> None:
        if not job.cookies_file or job.cookies_file.parent.resolve() != job.output_dir.resolve():
            return
        try:
            job.cookies_file.unlink(missing_ok=True)
        except OSError:
            log.exception("job=%s temporary cookies cleanup failed", job.id)
