import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

from ...domain.enums import JobStatus
from ...domain.models import DownloadJob
from .database import Database


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class JobRepository:
    def __init__(self, database: Database | Path):
        self.database = database if isinstance(database, Database) else Database(Path(database))

    async def initialize(self) -> None:
        await self.database.initialize()

    @staticmethod
    def _values(job: DownloadJob) -> tuple:
        return (
            job.id, job.youtube_url, job.video_id, job.title, job.channel_name,
            job.channel_url, job.thumbnail_url, _dt(job.scheduled_start),
            job.guild_id, job.channel_id, job.message_id, job.user_id,
            job.status.value, _dt(job.created_at), _dt(job.started_at),
            _dt(job.finished_at), str(job.output_dir), str(job.chat_file) if job.chat_file else None,
            str(job.archive_file) if job.archive_file else None, job.error,
            str(job.cookies_file) if job.cookies_file else None,
        )

    @staticmethod
    def _job(row: sqlite3.Row) -> DownloadJob:
        return DownloadJob(
            id=row["id"], youtube_url=row["youtube_url"], video_id=row["video_id"],
            title=row["title"], channel_name=row["channel_name"], channel_url=row["channel_url"],
            thumbnail_url=row["thumbnail_url"], scheduled_start=_parse(row["scheduled_start"]),
            guild_id=row["guild_id"], channel_id=row["channel_id"], message_id=row["message_id"],
            user_id=row["user_id"], status=JobStatus(row["status"]), created_at=_parse(row["created_at"]),
            started_at=_parse(row["started_at"]), finished_at=_parse(row["finished_at"]),
            output_dir=Path(row["output_dir"]),
            chat_file=Path(row["chat_file"]) if row["chat_file"] else None,
            archive_file=Path(row["archive_file"]) if row["archive_file"] else None,
            error=row["error"],
            cookies_file=Path(row["cookies_file"]) if row["cookies_file"] else None,
        )

    async def create(self, job: DownloadJob) -> None:
        await self.database.initialize()
        await asyncio.to_thread(self._write, job, False)

    async def update(self, job: DownloadJob) -> None:
        await self.database.initialize()
        await asyncio.to_thread(self._write, job, True)

    def _write(self, job: DownloadJob, update: bool) -> None:
        query = (
            "UPDATE jobs SET youtube_url=?,video_id=?,title=?,channel_name=?,channel_url=?,"
            "thumbnail_url=?,scheduled_start=?,guild_id=?,channel_id=?,message_id=?,user_id=?,"
            "status=?,created_at=?,started_at=?,finished_at=?,output_dir=?,chat_file=?,archive_file=?,error=?,cookies_file=? "
            "WHERE id=?"
        ) if update else (
            "INSERT INTO jobs (id,youtube_url,video_id,title,channel_name,channel_url,thumbnail_url,"
            "scheduled_start,guild_id,channel_id,message_id,user_id,status,created_at,started_at,finished_at,"
            "output_dir,chat_file,archive_file,error,cookies_file) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        )
        values = self._values(job)
        with sqlite3.connect(self.database.path) as connection:
            if update:
                connection.execute(query, values[1:] + (values[0],))
            else:
                connection.execute(query, values)
            connection.commit()

    async def get(self, job_id: str) -> DownloadJob | None:
        await self.database.initialize()
        return await asyncio.to_thread(self._get, job_id)

    def _get(self, job_id: str) -> DownloadJob | None:
        with sqlite3.connect(self.database.path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._job(row) if row else None

    async def find_active_by_video_id(self, video_id: str) -> DownloadJob | None:
        await self.database.initialize()
        return await asyncio.to_thread(self._find_active, video_id)

    def _find_active(self, video_id: str) -> DownloadJob | None:
        statuses = tuple(s.value for s in JobStatus if not s.terminal)
        marks = ",".join("?" for _ in statuses)
        with sqlite3.connect(self.database.path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                f"SELECT * FROM jobs WHERE video_id=? AND status IN ({marks}) ORDER BY created_at LIMIT 1",
                (video_id, *statuses),
            ).fetchone()
        return self._job(row) if row else None

    async def claim_video_id(self, job_id: str, video_id: str) -> DownloadJob | None:
        """Atomically associate a resolved video with a job.

        Resolving two requests concurrently must not allow both to pass the
        duplicate check between their metadata update and recording start.
        """
        await self.database.initialize()
        return await asyncio.to_thread(self._claim_video_id, job_id, video_id)

    def _claim_video_id(self, job_id: str, video_id: str) -> DownloadJob | None:
        statuses = tuple(s.value for s in JobStatus if not s.terminal)
        marks = ",".join("?" for _ in statuses)
        with sqlite3.connect(self.database.path, timeout=30) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                f"SELECT * FROM jobs WHERE video_id=? AND id<>? AND status IN ({marks}) "
                "ORDER BY created_at LIMIT 1",
                (video_id, job_id, *statuses),
            ).fetchone()
            if row:
                connection.rollback()
                return self._job(row)
            connection.execute("UPDATE jobs SET video_id=? WHERE id=?", (video_id, job_id))
            connection.commit()
        return None

    async def mark_non_terminal_jobs_failed_on_startup(self) -> None:
        await self.database.initialize()
        await asyncio.to_thread(self._mark_restarted)

    def _mark_restarted(self) -> None:
        statuses = tuple(s.value for s in JobStatus if not s.terminal)
        marks = ",".join("?" for _ in statuses)
        with sqlite3.connect(self.database.path) as connection:
            connection.execute(
                f"UPDATE jobs SET status=?, error=? WHERE status IN ({marks})",
                (JobStatus.FAILED.value, "Bot restarted", *statuses),
            )
            connection.commit()
