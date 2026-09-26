import asyncio
from pathlib import Path
from typing import Any


class DiscordUploadPolicy:
    def __init__(self, fallback: int | None = None):
        self.fallback = fallback

    def get_max_file_size(self, guild: Any | None) -> int:
        limit = getattr(guild, "filesize_limit", None)
        if limit:
            return int(limit)
        if self.fallback is None:
            raise ValueError("DISCORD_MAX_FILE_SIZE must be configured when no guild limit is available")
        return self.fallback


class DiscordUploadError(RuntimeError):
    pass


class DiscordUploader:
    def __init__(self, bot: Any, policy: DiscordUploadPolicy | None = None):
        self.bot = bot
        self.policy = policy

    def get_guild(self, guild_id: int) -> Any | None:
        return self.bot.get_guild(guild_id)

    async def upload_to_job_message(self, job: Any, files: list[Path]) -> None:
        try:
            channel = await self.bot.fetch_channel(job.channel_id)
            message = await channel.fetch_message(job.message_id)
            import discord
            attachments = [discord.File(str(path), filename=path.name) for path in files]
            try:
                await message.edit(attachments=attachments)
            finally:
                for attachment in attachments:
                    close = getattr(attachment, "close", None)
                    if close:
                        result = close()
                        if asyncio.iscoroutine(result):
                            await result
        except Exception as exc:
            raise DiscordUploadError(str(exc)) from exc
