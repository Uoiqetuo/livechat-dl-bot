# Discord YouTube Live Chat Downloader

## 1. Project Overview

建立一個執行於 VPS 的 Python Discord Bot。

Bot 的主要功能：

1. 使用者透過 Discord 指令：

   ```text
   !dl <YouTube URL>
   ```

   建立一個 YouTube Live Chat recording job。

2. 使用 `yt-dlp` Python API：

   * 不下載影片
   * 不下載音訊
   * 只下載 YouTube Live Chat
   * 使用：

   ```python
   {
       "writesubtitles": True,
       "subtitleslangs": ["live_chat"],
       "skip_download": True,
       "ignore_no_formats_error": True,
       "noprogress": True,
   }
   ```

3. 同時支援多個直播錄製。

4. yt-dlp 完成後取得：

   ```text
   <video_id>.live_chat.json
   ```

5. 將 `.live_chat.json` 壓縮成完整 ZIP。

6. 如果完整 ZIP 超過 Discord 當前可用的單檔附件限制：

   * 建立暫時性的分割壓縮檔
   * 將所有分割檔上傳到同一則 Discord Job message
   * 上傳完成後刪除所有分割檔
   * 原始 `.live_chat.json` 也刪除
   * VPS 最終只保留完整 ZIP

7. Job 建立時建立一則 Discord message。

8. Discord message 使用 Embed 顯示：

   * 當前狀態
   * 影片標題與影片連結
   * 平台與頻道名稱、頻道連結
   * 預計直播開始時間
   * 直播錄製完成後顯示錄製結束時間
   * 影片封面
   * 訊息最後更新時間

9. Discord message 只在必要時更新，例如：

   * Job 狀態改變
   * YouTube metadata 解析完成
   * 錄製完成
   * 壓縮完成
   * 上傳完成
   * Job 失敗
   * Job 被取消

10. Discord message 不顯示錄製或下載進度。

11. 所有完成後的檔案使用 Discord `Message.edit()` 放到原本建立 Job 的同一則 message。

12. Bot 重啟時不恢復進行中的 Job。

13. 使用者取消 Job 時：

* 停止錄製
* 已產生的 `.live_chat.json` 保留
* 不建立 ZIP
* 不上傳檔案
* Job 狀態為 `CANCELLED`

---

# 2. Technology Stack

Required:

* Python 3.12+
* `discord.py`
* `yt-dlp` 2025.11.12 or newer
* `yt-dlp-ejs` 0.8.0 or newer
* Python `asyncio`
* SQLite
* Python standard library `zipfile`

Deployment must support:

* Docker
* Docker Compose
* direct CLI Python execution

YouTube extraction uses yt-dlp's External JavaScript (EJS) support. The Docker
image must provide Node.js 20 or newer and the application must explicitly
select the Node.js runtime for yt-dlp. Local development does not install
Node.js automatically; developers must install Node.js separately and make
`node` available on `PATH`.

The application remains a single-process monolithic Python application with clear layer boundaries.

---

# 3. Architecture

Use four conceptual layers.

```text
Presentation
    ↓
Application
    ↓
Domain

Infrastructure
    ↑
Application
```

## Presentation

Responsible for Discord-specific behavior:

* `!dl` command
* Embed construction
* Discord UI View
* Cancel button
* Discord message editing
* Discord permission checks

Must not directly execute yt-dlp.

## Application

Responsible for business workflows:

* Job creation
* Job execution
* Job state transitions
* Concurrent job management
* Cancellation
* Compression
* Archive upload
* File cleanup

## Domain

Contains pure business models and enums.

Must not import:

* `discord`
* `yt_dlp`
* SQLite implementation

## Infrastructure

Contains external implementations:

* yt-dlp
* SQLite
* filesystem
* ZIP
* Discord upload

---

# 4. Directory Structure

Implement:

```text
livechat-dl-bot/
│
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── Dockerfile
├── compose.yaml
│
├── src/
│   └── livechat_bot/
│       │
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       │
│       ├── presentation/
│       │   └── discord/
│       │       ├── __init__.py
│       │       ├── bot.py
│       │       ├── commands.py
│       │       ├── views.py
│       │       └── embeds.py
│       │
│       ├── application/
│       │   ├── __init__.py
│       │   ├── download_service.py
│       │   ├── job_manager.py
│       │   ├── archive_service.py
│       │   └── upload_service.py
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   ├── download_job.py
│       │   │   └── stream_info.py
│       │   │
│       │   └── enums/
│       │       ├── __init__.py
│       │       └── job_status.py
│       │
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   │
│       │   ├── youtube/
│       │   │   ├── __init__.py
│       │   │   └── ytdlp_client.py
│       │   │
│       │   ├── persistence/
│       │   │   ├── __init__.py
│       │   │   ├── database.py
│       │   │   └── job_repository.py
│       │   │
│       │   ├── archive/
│       │   │   ├── __init__.py
│       │   │   └── zip_service.py
│       │   │
│       │   └── discord/
│       │       ├── __init__.py
│       │       └── uploader.py
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logging.py
│           └── filesystem.py
│
├── data/
│   ├── database.sqlite3
│   └── jobs/
│
└── tests/
    ├── unit/
    └── integration/
```

---

# 5. Domain Model

## 5.1 JobStatus

Create:

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    RESOLVING = "resolving"
    RECORDING = "recording"
    COMPRESSING = "compressing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

Terminal states:

```text
COMPLETED
FAILED
CANCELLED
```

Non-terminal states:

```text
PENDING
RESOLVING
RECORDING
COMPRESSING
UPLOADING
```

---

# 6. StreamInfo

Create a pure domain model:

```python
@dataclass
class StreamInfo:
    video_id: str
    video_url: str
    title: str
    channel_name: str | None
    channel_url: str | None
    thumbnail_url: str | None
    scheduled_start: datetime | None
    live_status: str | None
```

The model must not contain raw yt-dlp objects.

---

# 7. DownloadJob

Create:

```python
@dataclass
class DownloadJob:
    id: str

    youtube_url: str
    video_id: str | None

    title: str | None
    channel_name: str | None
    channel_url: str | None
    thumbnail_url: str | None
    scheduled_start: datetime | None

    guild_id: int
    channel_id: int
    message_id: int
    user_id: int

    status: JobStatus

    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    output_dir: Path

    chat_file: Path | None
    archive_file: Path | None

    error: str | None
```

`message_id` 必須保存，因為每個 Job 對應一則 Discord message。

`archive_file` 指向最終完整 ZIP。

---

# 8. Job Lifecycle

正常流程：

```text
PENDING
   ↓
RESOLVING
   ↓
RECORDING
   ↓
COMPRESSING
   ↓
UPLOADING
   ↓
COMPLETED
```

任何階段發生未處理錯誤：

```text
FAILED
```

取消：

```text
PENDING      → CANCELLED
RESOLVING    → CANCELLED
RECORDING    → CANCELLED
```

以下狀態不可取消：

```text
COMPRESSING
UPLOADING
COMPLETED
FAILED
CANCELLED
```

---

# 9. yt-dlp Integration

Implement:

```text
infrastructure/youtube/ytdlp_client.py
```

Create:

```python
class YTDLPClient:

    async def get_stream_info(
        self,
        url: str,
        cookies_file: Path | None = None,
    ) -> StreamInfo:
        ...

    async def download_live_chat(
        self,
        url: str,
        output_dir: Path,
        cancel_event: asyncio.Event,
        cookies_file: Path | None = None,
    ) -> Path:
        ...
```

Underlying yt-dlp operations are synchronous and must not block the Discord asyncio event loop.

Use:

```python
await asyncio.to_thread(...)
```

around blocking yt-dlp operations where appropriate.

---

# 10. yt-dlp Options

Live Chat download must use:

```python
ydl_opts = {
    "writesubtitles": True,
    "subtitleslangs": ["live_chat"],
    "skip_download": True,
    "ignore_no_formats_error": True,
    "noprogress": True,
    "js_runtimes": {"node": {}},
}
```

The same `js_runtimes` option must be used for metadata resolution and live
chat download. If `cookies_file` is provided, pass it to yt-dlp as
`"cookiefile": str(cookies_file)`. If a proxy is configured, pass it to both
calls as `"proxy": proxy`.

The output filename must be based on the YouTube video ID.

Expected file:

```text
<video_id>.live_chat.json
```

Do not download:

* video
* audio
* local thumbnail files
* unrelated subtitle tracks

The thumbnail URL is used directly by Discord Embed.

---

# 11. yt-dlp Metadata

During resolving, obtain:

* video ID
* video URL
* title
* channel name
* channel URL
* thumbnail URL
* scheduled start timestamp
* live status

Convert the raw yt-dlp metadata into:

```python
StreamInfo
```

Do not expose the raw yt-dlp `InfoDict` outside Infrastructure.

---

# 12. Job Storage

Use SQLite.

Schema:

```sql
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,

    youtube_url TEXT NOT NULL,
    video_id TEXT,

    title TEXT,
    channel_name TEXT,
    channel_url TEXT,
    thumbnail_url TEXT,
    scheduled_start TEXT,

    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,

    status TEXT NOT NULL,

    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,

    output_dir TEXT NOT NULL,
    chat_file TEXT,
    archive_file TEXT,

    error TEXT
);
```

Create repository abstraction:

```python
class JobRepository:

    async def create(
        self,
        job: DownloadJob,
    ) -> None:
        ...

    async def get(
        self,
        job_id: str,
    ) -> DownloadJob | None:
        ...

    async def update(
        self,
        job: DownloadJob,
    ) -> None:
        ...

    async def find_active_by_video_id(
        self,
        video_id: str,
    ) -> DownloadJob | None:
        ...

    async def mark_non_terminal_jobs_failed_on_startup(
        self,
    ) -> None:
        ...
```

---

# 13. Persistence Rules

Persist important Job state transitions.

Example:

```text
PENDING
↓
database update
↓
RESOLVING
↓
database update
↓
RECORDING
↓
database update
```

The following information must be persisted after metadata resolution:

* video ID
* title
* channel name
* channel URL
* thumbnail URL
* scheduled start time

Persist:

* start time
* finish time
* generated file paths
* errors
* current status

---

# 14. Job Directory

Each Job gets:

```text
data/jobs/YYYYMMDD/<job_id>/
```

Example:

```text
data/jobs/20260923/a81f2c/
```

During recording:

```text
a81f2c/
└── abc123.live_chat.json
```

After successful compression:

```text
a81f2c/
├── abc123.live_chat.json
└── abc123.zip
```

After successful upload:

```text
a81f2c/
└── abc123.zip
```

The final successful Job directory contains the complete ZIP only.

---

# 15. File Retention Rules

## Successful Job

After the complete workflow succeeds, retain:

```text
<video_id>.zip
```

Delete:

```text
<video_id>.live_chat.json
```

Delete all temporary split archive files.

The final ZIP must be the complete, unsplit archive.

---

## Cancelled Job

If cancellation happens while recording:

```text
<video_id>.live_chat.json
```

is retained if it exists.

Do not create a ZIP.

Do not upload the file.

The Job is marked:

```text
CANCELLED
```

---

## Failed Job

If recording fails and a `.live_chat.json` exists:

```text
<video_id>.live_chat.json
```

is retained.

If compression or upload fails after the JSON has been generated, retain generated files so that future manual recovery is possible.

Automatic cleanup of failed Jobs is outside the MVP.

---

# 16. JobManager

Implement:

```python
class JobManager:

    async def submit(
        self,
        job: DownloadJob,
    ) -> None:
        ...

    async def cancel(
        self,
        job_id: str,
    ) -> bool:
        ...

    def get_task(
        self,
        job_id: str,
    ) -> asyncio.Task | None:
        ...
```

Maintain runtime state:

```python
dict[str, asyncio.Task]
```

and:

```python
dict[str, asyncio.Event]
```

for cancellation.

Use:

```python
asyncio.Semaphore
```

to limit concurrent active Jobs.

Configuration:

```env
MAX_CONCURRENT_JOBS=5
```

---

# 17. Cancellation

Each active Job has:

```python
cancel_event = asyncio.Event()
```

Cancellation flow:

```text
Discord Cancel button
        ↓
JobManager.cancel(job_id)
        ↓
cancel_event.set()
        ↓
yt-dlp recording terminates
        ↓
check resulting .live_chat.json
        ↓
retain file
        ↓
status = CANCELLED
```

Do not:

* create ZIP
* upload archive
* delete the `.live_chat.json`

for a cancelled recording.

If no file was produced, there is no file to retain.

---

# 18. DownloadService

Implement:

```text
application/download_service.py
```

with:

```python
class DownloadService:

    async def run(
        self,
        job: DownloadJob,
        cancel_event: asyncio.Event,
    ) -> None:
        ...
```

Workflow:

```text
1. Set RESOLVING
2. Resolve StreamInfo
3. Update Job metadata
4. Update Discord message
5. Set RECORDING
6. Update Discord message
7. Start yt-dlp
8. Wait for live chat recording to finish
9. Check cancellation
10. Set COMPRESSING
11. Update Discord message
12. Create complete ZIP
13. Remove original JSON
14. Set UPLOADING
15. Update Discord message
16. Determine Discord upload size
17. If necessary, create temporary split archive files
18. Upload archive files to the original Discord message
19. Delete temporary split archive files
20. Set COMPLETED
21. Set finished_at
22. Update Discord message
```

Any unexpected exception:

```text
status = FAILED
error = safe error message
```

Detailed exception information is logged server-side.

---

# 19. Recording Completion

`finished_at` represents the actual time when the Live Chat recording ended.

It must be set when the yt-dlp recording process completes successfully.

It must NOT represent:

* ZIP creation time
* Discord upload time
* Job creation time

This timestamp is displayed as the Discord Embed field:

```text
結束於
```

---

# 20. Archive Service

Implement:

```text
infrastructure/archive/zip_service.py
```

with:

```python
class ZipService:

    async def create_zip(
        self,
        source_file: Path,
        destination: Path,
    ) -> Path:
        ...

    async def split_archive(
        self,
        archive: Path,
        max_size: int,
    ) -> list[Path]:
        ...
```

The complete ZIP must contain exactly:

```text
<video_id>.live_chat.json
```

Do not modify the JSON contents.

The original JSON is deleted only after the complete ZIP has been successfully created and validated.

---

# 21. Complete ZIP Requirement

The canonical archive is always:

```text
<video_id>.zip
```

This file must contain the complete `.live_chat.json`.

If Discord cannot accept the complete ZIP as one attachment, create temporary upload parts from the complete ZIP.

Example:

```text
Permanent:
abc123.zip

Temporary:
abc123.part01.zip
abc123.part02.zip
abc123.part03.zip
```

After Discord upload succeeds:

```text
abc123.zip
```

remains.

The `.partXX.zip` files are deleted.

---

# 22. Split Archive

If:

```text
archive_size <= max_file_size
```

upload:

```text
<video_id>.zip
```

directly.

If:

```text
archive_size > max_file_size
```

create:

```text
<video_id>.part01.zip
<video_id>.part02.zip
...
```

The split files must represent the complete canonical ZIP and be suitable for reconstruction.

Each part must remain below the configured Discord upload size, with a safety margin.

Use:

```text
max_part_size = discord_limit - safety_margin
```

The safety margin must be configurable.

---

# 23. Discord Upload Policy

Do not hard-code a universal Discord attachment size.

Implement:

```python
class DiscordUploadPolicy:

    def get_max_file_size(
        self,
        guild: discord.Guild | None,
    ) -> int:
        ...
```

Use the Discord API / library information available to determine the applicable upload limit.

Provide a configurable fallback:

```env
DISCORD_MAX_FILE_SIZE=
```

The fallback must be explicitly configured when runtime Discord information is unavailable.

---

# 24. DiscordUploader

Implement:

```text
infrastructure/discord/uploader.py
```

with:

```python
class DiscordUploader:

    async def upload_to_job_message(
        self,
        job: DownloadJob,
        files: list[Path],
    ) -> None:
        ...
```

Behavior:

1. Fetch the existing Discord message using:

   * channel ID
   * message ID

2. Open the upload files.

3. Edit the existing message.

4. Attach all archive files to that message.

Do not create another message.

Conceptually:

```python
await message.edit(
    embed=completed_embed,
    view=completed_view,
    attachments=attachments,
)
```

The upload files are temporary upload artifacts except for the canonical complete ZIP retained on disk.

---

# 25. Discord Embed Format

Implement:

```text
presentation/discord/embeds.py
```

with:

```python
def build_job_embed(
    job: DownloadJob,
) -> discord.Embed:
    ...
```

The Embed title is the current Job status.

Example:

```text
🔴 錄製中
```

The exact presentation strings should be centralized in the presentation layer.

---

# 26. Embed Fields

The Embed must contain the following fields in this order.

## Field 1

```text
title: 標題
value: <影片標題>
```

The video title must be a hyperlink to the YouTube video.

Discord Markdown format:

```text
[影片標題](https://www.youtube.com/...)
```

---

## Field 2

```text
title: YouTube
value: <頻道名稱>
```

The channel name must be a hyperlink to the YouTube channel.

Example:

```text
[頻道名稱](https://www.youtube.com/@...)
```

The field title represents the platform.

---

## Field 3

```text
title: 預計開始時間
value: <Discord timestamp>
```

Python format:

```python
f"<t:{timestamp}:F>"
```

The timestamp must be generated from `scheduled_start`.

Use a Unix timestamp.

If YouTube does not provide a scheduled start time, display an explicit fallback such as:

```text
未知
```

Do not fabricate a timestamp.

---

## Field 4

Only display after recording has completed.

```text
title: 結束於
value: <Discord timestamp>
```

Python format:

```python
f"<t:{timestamp}:F>"
```

The timestamp must represent `finished_at`.

Do not display this field while the Job is:

```text
PENDING
RESOLVING
RECORDING
```

---

# 27. Embed Image

Use the YouTube thumbnail as the Embed image:

```python
embed.set_image(
    url=job.thumbnail_url
)
```

Do not use `set_thumbnail()`.

The thumbnail URL is not downloaded to the VPS.

If no thumbnail is available, omit the image.

---

# 28. Embed Footer

The Embed footer displays the message update time.

Every time the Job message is actually edited, generate a new update timestamp.

Example:

```text
更新於 2026-09-23 16:30:12
```

The exact formatting may follow the project's timezone configuration.

The footer is presentation-only and is not persisted as Job state.

---

# 29. No Progress Display

The Discord message must not display:

* percentage
* downloaded bytes
* download speed
* ETA
* elapsed recording time
* number of chat messages
* file size progress
* progress bars

The Embed only communicates Job state and metadata.

---

# 30. Discord View

Implement:

```text
presentation/discord/views.py
```

Create:

```python
class DownloadView(discord.ui.View):
    ...
```

The View contains a Cancel button:

```text
[ 取消錄製 ]
```

The button is enabled during:

```text
PENDING
RESOLVING
RECORDING
```

The button is disabled during:

```text
COMPRESSING
UPLOADING
COMPLETED
FAILED
CANCELLED
```

The View must call Application-layer cancellation logic.

It must not directly terminate yt-dlp.

---

# 31. Cancel Permission

By default, only the user who created the Job can cancel it.

Optional administrator / configured role cancellation may be supported through configuration.

The authorization decision belongs in the Presentation layer.

The JobManager remains responsible for performing the actual cancellation.

---

# 32. Discord Message Lifecycle

One Job corresponds to exactly one Discord message.

Flow:

```text
!dl URL
   ↓
Create Job
   ↓
Create initial Discord message
   ↓
Save message_id
   ↓
Start background Job
```

All later changes use:

```python
message.edit(...)
```

Do not create separate status messages.

---

# 33. Initial Discord Message

Immediately after accepting `!dl`, create a Job message.

The initial Embed may contain:

```text
Title: ⏳ 等待中
```

and fields populated with available metadata.

After YouTube metadata is resolved, update the same message with:

* title
* channel
* channel URL
* thumbnail
* scheduled start time

The message should then display the appropriate current status.

---

# 34. UI Update Policy

Only update the Discord message at these lifecycle events:

```text
Job created
Recording
Job completed
Job failed
Job cancelled
```

`Job created` is the initial message sent by the `!dl` command. The existing
message is edited when recording starts and at the terminal events above.
Other intermediate status changes (`RESOLVING`, `COMPRESSING`, and `UPLOADING`)
are persisted but do not update the Discord message.

Do not perform periodic updates merely to update a progress indicator.

The footer update time changes only when an actual message update occurs.

---

# 35. `!dl` Command

Command:

```text
!dl [-c] <youtube_url>

`-c` 使用由 `COOKIES_FILE` 直接指定的 Netscape 格式 cookies 檔案；
省略時不使用 cookies。cookies 路徑必須指向 `.txt` 或 `.cookies` 檔案，
檔案不存在或不可讀時不建立 job。

建立 job 時會將 cookies 複製到該 job 的暫存目錄，yt-dlp 使用此副本
作為 `cookiefile`，避免更新原始設定檔；job 結束後刪除暫存副本。
```

Responsibilities:

1. Validate input.
2. Create Job.
3. Create initial Discord message.
4. Save Discord message ID.
5. Submit Job to JobManager.
6. Return immediately.

The command handler must not wait until the livestream ends.

Correct architecture:

```python
await job_manager.submit(job)
```

The actual recording executes as a background task.

---

# 36. URL Validation

Accept YouTube URLs supported by yt-dlp.

Do not implement an unnecessarily restrictive URL parser.

Basic validation may reject obviously invalid input.

yt-dlp remains the authoritative resolver.

---

# 37. Duplicate Recording Protection

Do not allow multiple active Jobs for the same YouTube `video_id`.

Before starting a recording:

```text
find_active_by_video_id(video_id)
```

If an active Job exists, reject the new request and identify the existing Job.

Active statuses:

```text
PENDING
RESOLVING
RECORDING
COMPRESSING
UPLOADING
```

Terminal Jobs do not block a new Job for the same video ID.

---

# 38. Commands

The MVP exposes:

```text
!dl <youtube_url>
```

No additional Job management commands are required.

Job management is performed through the Job message and its View.

---

# 39. Error Handling

Define meaningful exceptions where useful:

```text
InvalidYouTubeUrl
VideoNotFound
StreamResolutionError
LiveChatDownloadError
ArchiveError
ArchiveSplitError
DiscordUploadError
JobNotFound
JobAlreadyRunning
JobCancellationError
```

Do not expose raw stack traces to Discord users.

Log detailed exceptions server-side.

Discord users receive concise error information.

---

# 40. Logging

Use Python `logging`.

Job-related logs should include:

```text
job_id
video_id
status
```

Example:

```text
INFO job=a81f2c video=abc123 status=recording
Live chat recording started
```

Do not log:

* Discord bot token
* environment secrets
* credentials

---

# 41. Filesystem Safety

All generated paths must be based on trusted identifiers.

Do not use raw:

* YouTube title
* channel name
* arbitrary user input

as filesystem paths.

Job path:

```text
data/jobs/YYYYMMDD/<job_id>/
```

File names:

```text
<video_id>.live_chat.json
<video_id>.zip
<video_id>.part01.zip
```

---

# 42. Disk Space

Before starting a Job, check available filesystem space.

Configuration:

```env
MIN_FREE_DISK_GB=5
```

If insufficient space is available:

```text
status = FAILED
```

and do not start recording.

No automatic deletion of historical files is performed.

---

# 43. Concurrency

Use:

```python
asyncio.Semaphore
```

Configuration:

```env
MAX_CONCURRENT_JOBS=5
```

Multiple livestreams may be recorded concurrently, subject to the configured limit.

The Discord event loop must remain responsive regardless of recording duration.

---

# 44. Async / Blocking Rule

Never execute long-running blocking operations directly on the Discord event loop.

Potential blocking operations include:

* yt-dlp
* ZIP compression
* archive splitting
* large filesystem operations

Use:

```python
await asyncio.to_thread(...)
```

where appropriate.

Discord API operations remain asynchronous.

---

# 45. Startup Behavior

On startup:

```text
1. Load configuration
2. Initialize logging
3. Initialize SQLite
4. Mark non-terminal Jobs as FAILED
5. Start Discord bot
```

Non-terminal Jobs from the previous process are changed to:

```text
FAILED
```

with:

```text
error = "Bot restarted"
```

Do not resume:

* yt-dlp
* recording
* compression
* uploading

---

# 46. Shutdown Behavior

On graceful shutdown:

1. Stop accepting new Jobs.
2. Signal active recording Jobs to cancel.
3. Wait for active Jobs to terminate within a configurable timeout.
4. Preserve generated `.live_chat.json` files.
5. Exit.

Jobs that do not terminate before the timeout will be marked `FAILED` during the next startup.

---

# 47. Upload Failure

If recording and compression succeed but Discord upload fails:

```text
status = FAILED
```

Keep:

```text
<video_id>.zip
```

and any generated temporary split files that are needed for diagnosis or future manual recovery.

The implementation should clean temporary split files when upload succeeds.

Do not retry indefinitely.

Use a bounded retry policy for transient Discord failures.

---

# 48. Successful File Cleanup

Successful workflow:

```text
Recording
    ↓
abc123.live_chat.json
    ↓
Create complete ZIP
    ↓
abc123.zip
    ↓
Delete abc123.live_chat.json
    ↓
Determine Discord limit
    ↓
Fits limit?
    │
    ├── YES
    │    ↓
    │  upload abc123.zip
    │
    └── NO
         ↓
       create temporary parts
         ↓
       upload parts
         ↓
       delete parts
    ↓
COMPLETED
```

Final filesystem state:

```text
data/jobs/20260923/a81f2c/
└── abc123.zip
```

---

# 49. Configuration

Use `.env`.

Minimum configuration:

```env
DISCORD_TOKEN=

MAX_CONCURRENT_JOBS=5

MIN_FREE_DISK_GB=5

DISCORD_MAX_FILE_SIZE=

DISCORD_UPLOAD_RETRY_COUNT=3

DISCORD_UI_TIMEZONE=Asia/Taipei
```

Optional permission configuration may be added if required.

Optional proxy configuration is documented in section 60.

Do not hard-code credentials.

---

# 50. Main Dependency Wiring

`main.py` constructs dependencies.

Conceptually:

```python
config = Config.load()

repository = JobRepository(...)
youtube = YTDLPClient(...)
zip_service = ZipService(...)
uploader = DiscordUploader(...)
archive_service = ArchiveService(...)
download_service = DownloadService(...)
job_manager = JobManager(...)
```

Inject dependencies into:

* command handlers
* Views
* Application services

Do not instantiate service objects inside command callbacks.

---

# 51. Dependency Direction

Allowed:

```text
commands
    → DownloadService
    → JobManager

DownloadService
    → YTDLPClient
    → ArchiveService
    → DiscordUploader
    → JobRepository

Infrastructure
    → external libraries
```

Not allowed:

```text
YTDLPClient → discord.py
ZipService → discord.py
Domain → discord.py
Domain → yt-dlp
Domain → SQLite implementation
```

---

# 52. Testing Requirements

## Unit Tests

Test at minimum:

### Job state transitions

```text
valid transitions
invalid transitions
terminal state behavior
```

### Duplicate detection

```text
active same video ID → rejected
terminal same video ID → allowed
```

### Archive creation

Test:

```text
valid JSONL → complete ZIP
ZIP contains exactly the JSON file
original JSON deletion occurs only after successful ZIP creation
```

### Archive splitting

Test:

```text
small archive
archive over limit
multiple parts
part size safety margin
```

### Cancellation

Test:

```text
cancel before recording
cancel during recording
partial JSON retained
no ZIP created
no upload performed
```

### Successful cleanup

Test:

```text
JSON exists before archive
complete ZIP exists after archive
JSON removed after successful archive
split parts removed after successful upload
complete ZIP remains
```

### Startup recovery

Test:

```text
RECORDING → FAILED
COMPRESSING → FAILED
UPLOADING → FAILED
COMPLETED remains COMPLETED
FAILED remains FAILED
CANCELLED remains CANCELLED
```

---

# 53. Integration Tests

Where practical, test:

```text
!dl
    ↓
Job creation
    ↓
fake yt-dlp
    ↓
fake .live_chat.json
    ↓
complete ZIP
    ↓
fake Discord upload
    ↓
COMPLETED
```

Tests must not require an actual YouTube livestream.

Use a fake YTDLP client.

---

# 54. Fake YTDLP Client

Example:

```python
class FakeYTDLPClient:

    async def get_stream_info(self, url):
        return StreamInfo(
            video_id="test123",
            video_url=url,
            title="Test Live",
            channel_name="Test Channel",
            channel_url="https://www.youtube.com/@test",
            thumbnail_url="https://example.com/thumb.jpg",
            scheduled_start=datetime.now(timezone.utc),
            live_status="is_live",
        )

    async def download_live_chat(
        self,
        url,
        output_dir,
        cancel_event,
    ):
        path = output_dir / "test123.live_chat.json"

        path.write_text(
            '{"message": "hello"}\n',
            encoding="utf-8",
        )

        return path
```

---

# 55. Deployment

The application must support three deployment modes.

## Docker

Provide:

```text
Dockerfile
```

The container must run the Python application.

The image must include Node.js 20 or newer for yt-dlp EJS support. The
application must be configured to use Node.js rather than relying on yt-dlp's
default runtime selection.

Persistent data must be stored outside the container filesystem through a volume.

At minimum:

```text
/data
```

must be persistent.

---

## Docker Compose

Provide:

```text
compose.yaml
```

Example architecture:

```text
discord-livechat-bot
        │
        ├── application container
        │
        └── persistent volume
             └── /data
```

The Discord token must be supplied through environment variables or an `.env` file.

---

## Direct CLI

The project must support:

```bash
python -m livechat_bot
```

or an equivalent documented command.

Direct CLI/local development requires a separately installed Node.js 20 or
newer runtime. The project must not download or install Node.js as part of the
Python setup.

The README must document:

```text
installation
environment variables
database initialization
starting the bot
```

---

# 56. Persistent Data in Docker

The following must survive container recreation:

```text
data/database.sqlite3
data/jobs/
```

Do not store Job data only inside the container's ephemeral filesystem.

---

# 57. README Requirements

README must contain:

1. Project description.
2. Required Python version.
3. Discord Bot setup.
4. Required Discord permissions.
5. Environment variables.
6. Direct Python execution.
7. Docker execution.
8. Docker Compose execution.
9. Data directory structure.
10. Backup considerations.
11. Troubleshooting.
12. Testing instructions.

---

# 58. Coding Rules for the AI Agent

1. Keep business logic out of Discord callbacks.
2. Do not import `discord.py` from Domain.
3. Do not expose raw yt-dlp `InfoDict` outside Infrastructure.
4. Do not block the asyncio event loop.
5. A Job owns exactly one Discord message.
6. Do not create progress messages.
7. Do not display recording progress.
8. Persist important Job state transitions.
9. Preserve the complete ZIP for successful Jobs.
10. Delete the original JSON after successful archive creation.
11. Delete split archive files after successful Discord upload.
12. Preserve partial `.live_chat.json` for cancelled or failed recordings.
13. Do not automatically resume Jobs after restart.
14. Do not automatically delete historical completed ZIP files.
15. Do not use raw YouTube titles as filesystem paths.
16. Do not hard-code a universal Discord attachment limit.
17. Do not introduce unnecessary external services.
18. Keep infrastructure implementations replaceable.
19. Keep Discord presentation logic separate from Application logic.
20. Do not expose secrets or internal tracebacks to Discord users.

---

# 59. Definition of Done

The MVP is complete when:

```text
Discord
   │
   │ !dl <YouTube URL>
   ▼
Create Job
   │
   ▼
Create one Discord message
   │
   ├── Embed title = current status
   ├── 標題 → video title hyperlink
   ├── YouTube → channel hyperlink
   ├── 預計開始時間 → Discord timestamp
   ├── 完成後增加 結束於
   ├── Image = video thumbnail
   └── Footer = message update time
   │
   ▼
yt-dlp
   │
   ├── no video
   ├── no audio
   └── live_chat only
   │
   ▼
.live_chat.json
   │
   ▼
Complete ZIP
   │
   ├── fits Discord
   │      ↓
   │    upload complete ZIP
   │
   └── too large
          ↓
        create temporary split archives
          ↓
        upload all parts to same Discord message
          ↓
        delete split archives
   │
   ▼
Delete original .live_chat.json
   │
   ▼
Keep complete ZIP
   │
   ▼
COMPLETED
```

Cancellation:

```text
Cancel button
    ↓
stop yt-dlp
    ↓
retain .live_chat.json
    ↓
do not create ZIP
    ↓
do not upload
    ↓
CANCELLED
```

Restart:

```text
Bot restart
    ↓
no recovery
    ↓
previous non-terminal Jobs → FAILED
```

---

# 60. Outbound Proxy

YouTube may throttle or reject the `live_chat` endpoint when the host IP
belongs to a datacenter range, returning HTTP 403 or HTTP 503 even when the
cookies are valid. A proxy is therefore supported as an optional outbound path
for yt-dlp only.

Configuration:

```env
YOUTUBE_PROXY=socks5://warp:1080
```

Requirements:

* Read the proxy from the environment, never from source control.
* `YOUTUBE_PROXY` applies to yt-dlp only and takes precedence.
* `HTTPS_PROXY`, `https_proxy`, `HTTP_PROXY` and `http_proxy` are honoured as
  fallbacks, in that order, when `YOUTUBE_PROXY` is unset or empty.
* Accept `http`, `https`, `socks5` and `socks5h` URLs. No extra Python package
  is required; yt-dlp bundles its own SOCKS client.
* When unset, connect directly. The proxy must not change any behaviour other
  than the network path.
* Apply the proxy identically to metadata resolution and live chat download.
* Log the active proxy once at startup, with any credentials in the URL
  redacted. Never log the raw proxy URL.

Configuration reaches `YTDLPClient` through `Config.load()` and constructor
injection; `main.py` performs the wiring.

`compose.yaml` ships a commented-out Cloudflare WARP sidecar supplying such a
proxy, together with the matching `YOUTUBE_PROXY` and `depends_on` lines. All
three must be enabled together. The sidecar must run in proxy mode: it then
exposes a SOCKS5 listener and leaves the routing table and DNS untouched.
WARP's default mode replaces routes and DNS, which breaks a co-installed
Tailscale node. The WARP registration directory is host-mounted so the
registration survives restarts, and is excluded from source control and the
Docker build context.

The Discord UI contains no progress percentage, ETA, speed, byte count, progress bar, or chat-message count.

The implementation should treat this document as the source of truth. If a lower-level implementation detail is unspecified, choose the simplest implementation that preserves the architecture, Job lifecycle, persistence, Discord message lifecycle, and file-retention rules defined here.
