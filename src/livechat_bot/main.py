import asyncio

from .application.archive_service import ArchiveService
from .application.download_service import DownloadService
from .application.job_manager import JobManager
from .application.upload_service import UploadService
from .config import Config
from .infrastructure.archive.zip_service import ZipService
from .infrastructure.discord.uploader import DiscordUploadPolicy, DiscordUploader
from .infrastructure.persistence.database import Database
from .infrastructure.persistence.job_repository import JobRepository
from .infrastructure.youtube.ytdlp_client import YTDLPClient
from .presentation.discord.bot import create_bot
from .presentation.discord.embeds import build_job_embed
from .presentation.discord.views import DownloadView
from .utils.filesystem import has_minimum_free_space
from .utils.logging import configure_logging


async def run(config: Config) -> None:
    configure_logging()
    database = Database(config.data_dir / "database.sqlite3")
    repository = JobRepository(database)
    await repository.initialize()
    await repository.mark_non_terminal_jobs_failed_on_startup()
    youtube = YTDLPClient(config.proxy)
    archive = ArchiveService(ZipService())
    policy = DiscordUploadPolicy(config.discord_max_file_size)
    # The uploader is attached after bot construction.
    download = DownloadService(repository, youtube, archive, None,
                                None, lambda: has_minimum_free_space(config.data_dir, config.min_free_disk_gb))
    manager = JobManager(download, repository, config.max_concurrent_jobs)
    bot = create_bot(config, manager, repository)
    async def update_message(job):
        channel = await bot.fetch_channel(job.channel_id)
        message = await channel.fetch_message(job.message_id)
        await message.edit(embed=build_job_embed(job), view=DownloadView(manager, job))
    download.message_updater = update_message
    uploader = DiscordUploader(bot, policy)
    upload = UploadService(
        uploader, archive, policy, config.discord_upload_retry_count,
        config.discord_upload_safety_margin,
    )
    download.upload_service = upload
    try:
        await bot.start(config.discord_token)
    finally:
        await manager.shutdown(config.shutdown_timeout_seconds)


def main() -> None:
    asyncio.run(run(Config.load()))


if __name__ == "__main__":
    main()
