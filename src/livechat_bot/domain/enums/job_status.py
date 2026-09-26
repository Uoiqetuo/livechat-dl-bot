from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RESOLVING = "resolving"
    RECORDING = "recording"
    COMPRESSING = "compressing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in {self.COMPLETED, self.FAILED, self.CANCELLED}

    @property
    def cancellable(self) -> bool:
        return self in {self.PENDING, self.RESOLVING, self.RECORDING}
