import asyncio
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, youtube_url TEXT NOT NULL, video_id TEXT,
    title TEXT, channel_name TEXT, channel_url TEXT, thumbnail_url TEXT,
    scheduled_start TEXT, guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL, user_id INTEGER NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
    output_dir TEXT NOT NULL, chat_file TEXT, archive_file TEXT, error TEXT
    , cookies_file TEXT
)
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize)

    def _initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(SCHEMA)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)")}
            if "cookies_file" not in columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN cookies_file TEXT")
            connection.commit()
