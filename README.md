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

### Outbound proxy

If the host IP is a datacenter range, YouTube may throttle or reject the
`live_chat` endpoint with HTTP 403 or 503 even when cookies are valid. Set
`YOUTUBE_PROXY` to route yt-dlp through a proxy:

```env
YOUTUBE_PROXY=socks5://warp:1080
```

Accepted schemes are `http`, `https`, `socks5` and `socks5h`. yt-dlp ships its
own SOCKS client, so no extra Python package is required. `HTTPS_PROXY`,
`HTTP_PROXY` and their lowercase variants are honoured as fallbacks when
`YOUTUBE_PROXY` is unset. Leave it unset to connect directly. Only the proxy
host is logged at startup; credentials in the URL are redacted.

### Cloudflare WARP sidecar

`compose.yaml` ships a commented-out WARP service that provides such a proxy.
Uncomment the `warp` block, the `YOUTUBE_PROXY` line and `depends_on`
together, then:

```bash
docker compose up -d warp
# Registration needs a moment; the client must connect in full-tunnel mode first.
docker compose logs -f warp
```

Then switch WARP to proxy mode once. It persists in the `./warp` volume, so this
is a one-time bootstrap:

```bash
docker compose exec warp warp-cli --accept-tos mode proxy
docker compose exec warp warp-cli --accept-tos proxy port 40000
docker compose up -d --force-recreate warp
```

Proxy mode keeps the routing table and DNS untouched, so a co-installed
Tailscale node keeps working. WARP's default mode replaces both and breaks
Tailscale, so verify with `tailscale status` after any change.

GOST listens on `:1080` inside the compose network and forwards to the WARP
listener on `127.0.0.1:40000`. `docker/warp-healthcheck.sh` replaces the
image's built-in check with a real request through the proxy, and the container
restarts itself after three consecutive failures.

Verify the exit IP actually changed:

```bash
docker compose exec warp sh -c \
  'curl -s --socks5-hostname 127.0.0.1:1080 https://cloudflare.com/cdn-cgi/trace | grep -E "^(warp|ip)="'
```

`warp=on` together with a Cloudflare address instead of the host IP is the only
proof that requests are leaving through the tunnel.

Use `!dl <YouTube URL>` in a channel where the bot can post. The bot never
displays recording progress and does not resume jobs after restart; interrupted
jobs are marked failed at startup. Cancel from the button on the job message.

Tests:

```bash
pytest
```

If a job fails, inspect the application logs and retain the job directory for
manual recovery. Never put the bot token in source control.
