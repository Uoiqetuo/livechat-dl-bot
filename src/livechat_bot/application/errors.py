"""Stable application exception names for adapters and presentation code."""


class InvalidYouTubeUrl(ValueError):
    pass


class VideoNotFound(RuntimeError):
    pass


class StreamResolutionError(RuntimeError):
    pass


class LiveChatDownloadError(RuntimeError):
    pass


class ArchiveError(RuntimeError):
    pass


class ArchiveSplitError(RuntimeError):
    pass


class DiscordUploadError(RuntimeError):
    pass


class JobNotFound(RuntimeError):
    pass


class JobAlreadyRunning(RuntimeError):
    def __init__(self, job=None):
        self.job = job
        super().__init__(
            f"video already has active job {job.id}" if job is not None else "job already running"
        )


class JobCancellationError(RuntimeError):
    pass
