import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ...domain.enums import JobStatus
from ...domain.models import DownloadJob
from ...utils.filesystem import create_job_directory
from .embeds import build_job_embed
from .views import DownloadView


def register_commands(bot, config, job_manager, repository):
    parser = argparse.ArgumentParser(prog="!dl", add_help=False, exit_on_error=False)
    parser.add_argument("-c", "--cookies", action="store_true")
    parser.add_argument("youtube_url")

    def configured_cookies_file() -> Path:
        path = Path(config.cookies_file).expanduser().resolve()
        if path.suffix.lower() not in {".txt", ".cookies"}:
            raise ValueError("COOKIES_FILE must be a .txt or .cookies file")
        if not path.is_file() or not path.stat().st_mode & 0o444:
            raise ValueError("configured cookies file is missing or unreadable")
        return path

    @bot.command(name="dl")
    async def download_command(ctx, *, arguments: str = ""):
        try:
            args = parser.parse_args(arguments.split())
        except argparse.ArgumentError:
            await ctx.reply(parser.format_help())
            return
        cookies_file = None
        if args.cookies:
            try:
                cookies_file = configured_cookies_file()
            except ValueError as exc:
                await ctx.reply(f"cookies 設定錯誤：{exc}")
                return
        job_id = uuid4().hex[:12]
        output_dir = create_job_directory(config.data_dir, job_id)
        job_cookies_file = None
        if cookies_file:
            job_cookies_file = output_dir / ".cookies.txt"
            try:
                shutil.copy2(cookies_file, job_cookies_file)
            except OSError as exc:
                await ctx.reply(f"cookies 複製失敗：{exc}")
                return
        job = DownloadJob(
            id=job_id, youtube_url=args.youtube_url, video_id=None, title=None,
            channel_name=None, channel_url=None, thumbnail_url=None, scheduled_start=None,
            guild_id=ctx.guild.id if ctx.guild else 0, channel_id=ctx.channel.id,
            message_id=0, user_id=ctx.author.id, status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc), started_at=None, finished_at=None,
            output_dir=output_dir,
            cookies_file=job_cookies_file,
        )
        message = await ctx.reply(embed=build_job_embed(job), view=DownloadView(job_manager, job))
        job.message_id = message.id
        await repository.create(job)
        await job_manager.submit_existing(job)

    return download_command
