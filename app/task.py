from pathlib import Path
from typing import Any, cast
import asyncio
import logging

import discord
import yt_dlp
from yt_dlp.utils import DownloadCancelled

from archive_utils import ArchiveSplitResult, build_archive_and_split, cleanup_paths
from runtime_config import UPLOAD_TO_DISCORD
from status_view import StatusView

logger = logging.getLogger(__name__)

class Task():
    def __init__(self, url: str, ytdlp_opts: dict[str, Any], message: StatusView):
        self.url = url
        self.ytdlp_opts = ytdlp_opts
        self.message = message
        self._cancel_requested = False
        self._is_done = False
        self.downloaded_path: Path | None = None
        logger.info("Task created with URL: %s and options: %s", self.url, self.ytdlp_opts)
        

    async def run(self):
        logger.info("Running task for URL: %s with options: %s", self.url, self.ytdlp_opts)
        try:
            await self.message.update("下載中", f"正在下載 {self.url}")
            await self.download(self.url)
            if self._cancel_requested:
                await self.message.update("任務已取消", f"已取消下載 {self.url}")
            else:
                uploaded = await self.process_downloaded_file()
                if uploaded:
                    await self.message.update("任務完成", f"已完成下載 {self.url}")
                else:
                    await self.message.update("任務完成", f"已完成下載 {self.url}，未上傳到 Discord")

        except DownloadCancelled:
            await self.message.update("任務已取消", f"已取消下載 {self.url}")

        except Exception as e:
            logger.exception("Error downloading %s", self.url)
            title = "壓縮/上傳失敗" if self.downloaded_path is not None else "下載失敗"
            await self.message.update(title, f"{self.url}\n錯誤: {e}")
        finally:
            self._is_done = True
            await self.message.hide_controls()

    def _progress_hook(self, _data: dict[str, Any]):
        if _data.get("status") == "finished":
            filename = _data.get("filepath") or _data.get("filename")
            if filename:
                self.downloaded_path = Path(cast(str, filename))

        if self._cancel_requested:
            raise DownloadCancelled("Cancelled by user")

    def _download(self, url: str):
        opts = dict(self.ytdlp_opts)
        hooks = list(cast(list[Any], opts.get("progress_hooks", [])))
        hooks.append(self._progress_hook)
        opts["progress_hooks"] = hooks
        with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
            ydl.download([url])

    async def download(self, url: str):
        await asyncio.to_thread(self._download, url)

    async def process_downloaded_file(self) -> bool:
        if self.downloaded_path is None:
            raise RuntimeError("找不到已下載的檔案")

        downloaded_path = self.downloaded_path.expanduser().resolve()
        if not downloaded_path.exists():
            raise FileNotFoundError(f"下載檔案不存在: {downloaded_path}")

        if not UPLOAD_TO_DISCORD:
            await asyncio.to_thread(cleanup_paths, downloaded_path)
            return False

        split_result = await asyncio.to_thread(build_archive_and_split, downloaded_path)
        await self.upload_split_parts(split_result)
        await asyncio.to_thread(cleanup_paths, downloaded_path, *split_result.part_paths)
        return True

    async def upload_split_parts(self, split_result: ArchiveSplitResult):
        channel = self.message.message.channel
        if not isinstance(channel, discord.abc.Messageable):
            raise RuntimeError("目前頻道無法上傳檔案")

        for part_path in split_result.part_paths:
            await channel.send(file=discord.File(part_path, filename=part_path.name))

    async def cancel_download(self):
        if self._is_done:
            return False
        self._cancel_requested = True
        return True