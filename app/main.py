import asyncio
import logging
from app.runtime_config import LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from app.core.job_manager import job_manager_instance
from app.core.discord_bot import Bot


async def main():
    asyncio.create_task(job_manager_instance.start())

    bot = Bot()
    await bot.start_bot()


if __name__ == "__main__":
    asyncio.run(main())
