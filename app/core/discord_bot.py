import os
import logging
import discord
from discord.ext import commands

from app.core.cogs.dl import DownloadCog

logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="!",
            intents=intents,
        )

    async def setup_hook(self) -> None:
        await self.add_cog(DownloadCog(self))

    async def start_bot(self) -> None:
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError("DISCORD_TOKEN is not set in the environment variables.")

        await self.start(token)

    async def on_ready(self) -> None:
        logger.info("%s 已連接到以下伺服器:", self.user)
        for guild in self.guilds:
            logger.info(" - %s (ID: %s)", guild.name, guild.id)

    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("請提供 URL")
        elif isinstance(error, commands.CommandNotFound):
            return
        else:
            logger.exception("Command error", exc_info=error)
            await ctx.reply(f"發生錯誤：{error}")
