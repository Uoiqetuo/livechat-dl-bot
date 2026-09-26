# Discord YouTube Live Chat Downloader

Python 3.12+ Discord bot which records YouTube Live Chat with `yt-dlp`, creates
one canonical ZIP per job, and uploads it to the job's original Discord message.
The canonical ZIP is retained in `data/jobs/` after a successful upload.

## Setup

Create a Discord application and bot, enable the **Message Content Intent**, and
invite it with View Channel, Send Messages, Embed Links, Attach Files and Read
Message History permissions. Copy `.env.example` to `.env` and set
`DISCORD_TOKEN`. `DISCORD_MAX_FILE_SIZE` is required when Discord does not expose
the guild attachment limit (bytes).

Run directly:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[test]'
# Install Node.js separately; it is used by yt-dlp's EJS support.
python -m livechat_bot
```

Run with Docker Compose:

```bash
cp .env.example .env       # set DISCORD_TOKEN
docker compose up --build
```

The Docker image includes Node.js 22 and `yt-dlp-ejs` support for YouTube's
JavaScript challenges. Local development does not install Node.js automatically;
install Node.js 20 or newer separately and ensure `node` is available on `PATH`
before running the bot. See the
[yt-dlp EJS setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS) for runtime
requirements.

`DATA_DIR` contains `database.sqlite3` and dated `jobs/YYYYMMDD/<job-id>/`
directories. Back up this directory; completed ZIP files are not recreated
automatically. Configuration includes `MAX_CONCURRENT_JOBS`,
`MIN_FREE_DISK_GB`, `DISCORD_UPLOAD_RETRY_COUNT`, `DISCORD_UI_TIMEZONE`, and
`SHUTDOWN_TIMEOUT_SECONDS`.

To use authenticated YouTube access, place a Netscape-format cookies file at
the path configured by `COOKIES_FILE`. `!dl -c <YouTube URL>` uses that file;
`!dl <YouTube URL>` does not use cookies. The configured path must point to a
`.txt` or `.cookies` file. With Docker Compose, put the file in
`./cookies/cookies.txt`; the directory is mounted read-only at `/cookies` and
`COOKIES_FILE` is set to `/cookies/cookies.txt`.
When a job starts, the bot copies this file into the job directory and passes
the copy to yt-dlp, allowing yt-dlp to update the job-specific cookie file.
The temporary copy is deleted when the job ends.

Use `!dl <YouTube URL>` in a channel where the bot can post. The bot never
displays recording progress and does not resume jobs after restart; interrupted
jobs are marked failed at startup. Cancel from the button on the job message.

Tests:

```bash
pytest
```

If a job fails, inspect the application logs and retain the job directory for
manual recovery. Never put the bot token in source control.
