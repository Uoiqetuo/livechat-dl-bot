import argparse
from discord.ext import commands

from app.core.job_manager import job_manager_instance


class DownloadCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="!dl", add_help=False, exit_on_error=False
        )
        parser.add_argument("url", type=str, help="下載 URL")
        parser.add_argument(
            "-c", "--cookie", action="store_true", help="使用 Cookie 檔案"
        )
        return parser

    @commands.command(name="dl")
    async def download(self, ctx: commands.Context, *args: str):
        parser = self.create_parser()
        try:
            parsed_args = parser.parse_args(args)
        except argparse.ArgumentError:
            await ctx.reply(parser.format_help())
            return

        try:
            await job_manager_instance.create_job(
                url=parsed_args.url,
                use_cookie=parsed_args.cookie,
                message=ctx.message,
            )
        except FileNotFoundError:
            await ctx.reply("未設定 Cookie 檔案")
