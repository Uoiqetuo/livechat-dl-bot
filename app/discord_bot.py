import os
import logging

import discord
import asyncio

from conf import confs
from runtime_config import DOWNLOAD_DIR
from task import Task
from status_view import StatusView

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
                await message.channel.send("請提供 URL")
                return
            
            opts = confs.get("default", {}) | confs.get("chat", {})
            paths = dict(opts.get("paths", {}))
            paths["home"] = str(DOWNLOAD_DIR)
            opts["paths"] = paths
            status_view = await StatusView.create(message)
            task = Task(url, opts, status_view)
            status_view.set_task(task)
            asyncio.create_task(task.run())
            await message.edit(suppress=True)
            

    