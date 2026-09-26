import asyncio
from datetime import datetime, timezone

import pytest

from livechat_bot.application.archive_service import ArchiveService
from livechat_bot.application.download_service import DownloadService
from livechat_bot.application.upload_service import UploadService
from livechat_bot.domain.enums import JobStatus
from livechat_bot.domain.models import DownloadJob, StreamInfo
from livechat_bot.infrastructure.archive.zip_service import ZipService
from livechat_bot.infrastructure.persistence.job_repository import JobRepository


class FakeYouTube:
    async def get_stream_info(self, url, cookies_file=None):
        return StreamInfo("test123", url, "Test Live", "Test", "https://youtube.com/@test", None,
                          datetime.now(timezone.utc), "is_live")

    async def download_live_chat(self, url, output_dir, cancel_event, cookies_file=None):
        path = output_dir / "test123.live_chat.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"message":"hello"}\n')
        return path


class FakeUploader:
    def __init__(self):
        self.files = []

    async def upload_to_job_message(self, job, files):
        self.files.append(list(files))


class Policy:
    def get_max_file_size(self, guild):
        return 10_000_000


def make_job(tmp_path):
    return DownloadJob("job", "https://youtube.com/watch?v=test123", None, None, None, None, None, None,
                       1, 2, 3, 4, JobStatus.PENDING, datetime.now(timezone.utc), None, None, tmp_path / "job")


@pytest.mark.asyncio
async def test_fake_end_to_end_retains_canonical_archive(tmp_path):
    repository = JobRepository(tmp_path / "db.sqlite3")
    uploader = FakeUploader()
    archive = ArchiveService(ZipService())
    upload = UploadService(uploader, archive, Policy(), retry_count=1)
    job = make_job(tmp_path)
    await repository.create(job)
    updates = []

    async def update_message(updated_job):
        updates.append(updated_job.status)

    await DownloadService(
        repository, FakeYouTube(), archive, upload, message_updater=update_message
    ).run(job, asyncio.Event())
    assert job.status is JobStatus.COMPLETED
    assert updates == [JobStatus.RECORDING, JobStatus.COMPLETED]
    assert job.archive_file.exists()
    assert not list(job.output_dir.glob("*.live_chat.json"))
    assert uploader.files and uploader.files[0][0] == job.archive_file


@pytest.mark.asyncio
async def test_temporary_cookies_are_removed_after_download(tmp_path):
    repository = JobRepository(tmp_path / "db.sqlite3")
    archive = ArchiveService(ZipService())
    upload = UploadService(FakeUploader(), archive, Policy(), retry_count=1)
    job = make_job(tmp_path)
    job.output_dir.mkdir()
    job.cookies_file = job.output_dir / ".cookies.txt"
    job.cookies_file.write_text("temporary cookies")
    await repository.create(job)

    await DownloadService(repository, FakeYouTube(), archive, upload).run(job, asyncio.Event())

    assert not job.cookies_file.exists()


class CancelYouTube(FakeYouTube):
    async def download_live_chat(self, url, output_dir, cancel_event):
        path = output_dir / "test123.live_chat.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"partial":true}\n')
        cancel_event.set()
        raise RuntimeError("stopped")


@pytest.mark.asyncio
async def test_cancelled_recording_keeps_partial_json_and_does_not_upload(tmp_path):
    repository = JobRepository(tmp_path / "db.sqlite3")
    uploader = FakeUploader()
    archive = ArchiveService(ZipService())
    upload = UploadService(uploader, archive, Policy(), retry_count=1)
    job = make_job(tmp_path)
    await repository.create(job)
    updates = []

    async def update_message(updated_job):
        updates.append(updated_job.status)

    await DownloadService(
        repository, CancelYouTube(), archive, upload, message_updater=update_message
    ).run(job, asyncio.Event())
    assert job.status is JobStatus.CANCELLED
    assert updates == [JobStatus.RECORDING, JobStatus.CANCELLED]
    assert list(job.output_dir.glob("*.live_chat.json"))
    assert not list(job.output_dir.glob("*.zip"))
    assert not uploader.files
