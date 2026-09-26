import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ...domain.models import StreamInfo
from ...utils.filesystem import safe_file_component


class StreamResolutionError(RuntimeError):
    pass


class LiveChatDownloadError(RuntimeError):
    pass


class YTDLPClient:
    async def get_stream_info(self, url: str, cookies_file: Path | None = None) -> StreamInfo:
        return await asyncio.to_thread(self._get_stream_info, url, cookies_file)

    def _get_stream_info(self, url: str, cookies_file: Path | None = None) -> StreamInfo:
        try:
            from yt_dlp import YoutubeDL
            options = {
                "quiet": True, "skip_download": True, "writesubtitles": False,
                "ignore_no_formats_error": True, "noprogress": True,
                "js_runtimes": {"node": {}},
            }
            if cookies_file:
                options["cookiefile"] = str(cookies_file)
            with YoutubeDL(options) as ydl:
                info: dict[str, Any] = ydl.extract_info(url, download=False)
        except Exception as exc:
            raise StreamResolutionError(str(exc)) from exc
        timestamp = info.get("release_timestamp") or info.get("scheduled_start_time")
        if isinstance(timestamp, str):
            try:
                scheduled = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                scheduled = None
        else:
            scheduled = datetime.fromtimestamp(timestamp, timezone.utc) if timestamp else None
        return StreamInfo(
            video_id=str(info["id"]), video_url=info.get("webpage_url") or url,
            title=info.get("title") or "Unknown title", channel_name=info.get("uploader") or info.get("channel"),
            channel_url=info.get("channel_url") or info.get("uploader_url"),
            thumbnail_url=info.get("thumbnail"), scheduled_start=scheduled,
            live_status=info.get("live_status"),
        )

    async def download_live_chat(self, url: str, output_dir: Path, cancel_event: asyncio.Event,
                                 cookies_file: Path | None = None) -> Path:
        return await asyncio.to_thread(self._download, url, Path(output_dir), cancel_event, cookies_file)

    def _download(self, url: str, output_dir: Path, cancel_event: asyncio.Event,
                  cookies_file: Path | None = None) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            from yt_dlp import YoutubeDL
            info_id: str | None = None

            def progress_hook(_: dict) -> None:
                if cancel_event.is_set():
                    raise LiveChatDownloadError("cancelled")

            opts = {
                "writesubtitles": True, "subtitleslangs": ["live_chat"], "skip_download": True, "ignore_no_formats_error": True, "noprogress": True,
                "outtmpl": str(output_dir / "%(id)s.%(ext)s"), "quiet": True,
                "progress_hooks": [progress_hook],
                "js_runtimes": {"node": {}},
            }
            if cookies_file:
                opts["cookiefile"] = str(cookies_file)
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                info_id = str(info.get("id")) if info else None
        except Exception as exc:
            if cancel_event.is_set():
                raise LiveChatDownloadError("cancelled") from exc
            raise LiveChatDownloadError(str(exc)) from exc
        if cancel_event.is_set():
            raise LiveChatDownloadError("cancelled")
        video_id = safe_file_component(info_id or "unknown")
        result = output_dir / f"{video_id}.live_chat.json"
        if not result.exists():
            candidates = list(output_dir.glob("*.live_chat.json"))
            if len(candidates) == 1:
                result = candidates[0]
            else:
                raise LiveChatDownloadError("yt-dlp did not produce a live chat file")
        return result
