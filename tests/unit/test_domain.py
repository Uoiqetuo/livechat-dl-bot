from datetime import datetime, timezone
from pathlib import Path

import pytest

from livechat_bot.domain.enums import JobStatus
from livechat_bot.domain.models import DownloadJob


def job(status=JobStatus.PENDING):
    return DownloadJob(
        "id", "https://youtu.be/x", "x", "title", None, None, None, None,
        1, 2, 3, 4, status, datetime.now(timezone.utc), None, None, Path("."),
    )


def test_valid_transitions_and_terminal_states():
    item = job()
    for status in (JobStatus.RESOLVING, JobStatus.RECORDING, JobStatus.COMPRESSING,
                   JobStatus.UPLOADING, JobStatus.COMPLETED):
        item.transition(status)
    assert item.status.terminal
    with pytest.raises(ValueError):
        item.transition(JobStatus.FAILED)


def test_cancellation_is_only_allowed_before_upload():
    assert all(job(status).status.cancellable for status in (
        JobStatus.PENDING, JobStatus.RESOLVING, JobStatus.RECORDING
    ))
    assert not job(JobStatus.COMPRESSING).status.cancellable
    assert not job(JobStatus.COMPLETED).status.cancellable
