from datetime import datetime, timezone

import pytest

from livechat_bot.domain.enums import JobStatus
from livechat_bot.domain.models import DownloadJob
from livechat_bot.infrastructure.persistence.job_repository import JobRepository


def make_job(tmp_path, identifier, status, video="video"):
    return DownloadJob(identifier, "https://youtube.com/watch?v=" + video, video,
                       "Title", "Channel", "https://youtube.com/@channel", None, None,
                       1, 2, 3, 4, status, datetime.now(timezone.utc), None, None, tmp_path)


@pytest.mark.asyncio
async def test_repository_round_trip_and_duplicate_detection(tmp_path):
    repository = JobRepository(tmp_path / "jobs.sqlite3")
    await repository.create(make_job(tmp_path, "one", JobStatus.RECORDING))
    assert (await repository.get("one")).video_id == "video"
    assert (await repository.find_active_by_video_id("video")).id == "one"

    terminal = make_job(tmp_path, "two", JobStatus.COMPLETED)
    await repository.create(terminal)
    assert (await repository.find_active_by_video_id("video")).id == "one"


@pytest.mark.asyncio
async def test_startup_recovery_only_marks_non_terminal(tmp_path):
    repository = JobRepository(tmp_path / "jobs.sqlite3")
    for status in JobStatus:
        await repository.create(make_job(tmp_path, status.value, status, status.value))
    await repository.mark_non_terminal_jobs_failed_on_startup()
    for status in JobStatus:
        result = await repository.get(status.value)
        assert result.status is (JobStatus.FAILED if not status.terminal else status)
