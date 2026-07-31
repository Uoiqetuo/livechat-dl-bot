import discord
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.job import Job


class StatusView(discord.ui.View):
    def __init__(self, message: discord.Message, button_cb, job: "Job"):
        super().__init__(timeout=None)
        self.message = message
        self.status_message: discord.Message | None = None
        self.button_cb = button_cb
        self.job = job
        self.show_controls = True
        self.attachments = []

    @classmethod
    async def create(cls, message: discord.Message, button_cb, job: "Job"):
        view = cls(message, button_cb, job)
        view.status_message = await message.reply(view=view, embed=view.embed)
        return view

    @property
    def embed(self) -> discord.Embed:
        now = datetime.now(timezone.utc)
        status_label = self.job.status.value if self.job.status else "未知"
        embed = discord.Embed(title=status_label, timestamp=now)

        title_value = self._markdown_link(
            self.job.video_title or "未知",
            self.job.video_url or self.job.url,
        )
        extractor_title = self.job.extractor_key or self.job.extractor or "未知平台"
        channel_value = self._markdown_link(
            self.job.channel_name or "未知",
            self.job.channel_url or self.job.url,
        )

        embed.add_field(name="標題", value=title_value, inline=False)
        embed.add_field(name=extractor_title, value=channel_value, inline=False)
        embed.add_field(
            name="預計開始時間",
            value=self._discord_timestamp(self.job.planned_start_timestamp),
            inline=False,
        )

        finished_timestamp = self._finished_timestamp()
        if finished_timestamp is not None:
            embed.add_field(
                name="結束於",
                value=self._discord_timestamp(finished_timestamp),
                inline=False,
            )

        if self.job.video_id:
            embed.set_image(
                url=self.job.thumbnail_url
                or f"https://i.ytimg.com/vi/{self.job.video_id}/maxresdefault.jpg"
            )
        elif self.job.thumbnail_url:
            embed.set_image(url=self.job.thumbnail_url)

        embed.set_footer(text="更新於")

        return embed

    def _finished_timestamp(self) -> int | None:
        if self.job.recording_finished_at is None:
            return None

        if self.job.live_status == "was_live":
            if self.job.release_timestamp is not None and self.job.duration is not None:
                return int(self.job.release_timestamp + self.job.duration)
            return int(self.job.recording_finished_at.timestamp())

        if self.job.live_status in {"is_upcoming", "is_live"}:
            return int(self.job.recording_finished_at.timestamp())

        return int(self.job.recording_finished_at.timestamp())

    @staticmethod
    def _markdown_link(text: str, url: str) -> str:
        return f"[{text}]({url})"

    @staticmethod
    def _discord_timestamp(timestamp: int | None) -> str:
        if timestamp is None:
            return "未知"
        return f"<t:{timestamp}:F>"

    async def submit(self, attachment: bool = False):
        kwargs: dict[str, Any] = {"embed": self.embed, "view": self}
        if not self.show_controls:
            kwargs["view"] = None
        if attachment:
            kwargs["attachments"] = self.attachments

        if self.status_message is not None:
            await self.status_message.edit(**kwargs)

    @discord.ui.button(label="取消", style=discord.ButtonStyle.danger)
    async def button_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        button.disabled = True
        await interaction.response.defer()

        if self.button_cb:
            await self.button_cb()

        self.show_controls = False
