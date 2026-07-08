import os
import logging

import discord

from app.core.job_manager import job_manager_instance
from app.conf import confs
from app.runtime_config import DOWNLOAD_DIR

logger = logging.getLogger(__name__)


class Bot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

    async def start_bot(self):
        TOKEN = os.getenv("DISCORD_TOKEN")
        if not TOKEN:
            raise ValueError("DISCORD_TOKEN is not set in the environment variables.")
        await self.start(TOKEN)

    async def on_ready(self):
        logger.info("%s 已連接到以下伺服器:", self.user)
        for guild in self.guilds:
            logger.info(" - %s (ID: %s)", guild.name, guild.id)

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        if message.content.startswith("!dl"):
            url = message.content.split()[1]
            if not url:
                await message.reply("請提供 URL")
                return

            opts = confs.get("default", {}) | confs.get("chat", {})
            paths = dict(opts.get("paths", {}))
            paths["home"] = str(DOWNLOAD_DIR)
            opts["paths"] = paths

            await job_manager_instance.create_job(url, opts, message)
