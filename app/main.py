
import logging

import asyncio

from discord_bot import Bot
from runtime_config import LOG_LEVEL


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main():
    bot = Bot()
    asyncio.run(bot.start_bot())


if __name__ == "__main__":
    main()
