from typing import Any

import discord
from discord.ext import commands

from .commands import register_commands


def create_bot(config: Any, job_manager: Any, repository: Any) -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix=config.command_prefix, intents=intents)
    register_commands(bot, config, job_manager, repository)
    return bot
