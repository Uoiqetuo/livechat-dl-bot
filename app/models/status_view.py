import discord
from datetime import datetime
from typing import Any


class StatusView(discord.ui.View):
    def __init__(self, message: discord.Message, button_cb):
        super().__init__(timeout=None)
        self.message = message
        self.status_message: discord.Message | None = None
        self.button_cb = button_cb
        self.show_controls = True
        self.title = "成功建立任務"
        self.description = "任務已建立"
        self.embed = discord.Embed(
            description=self.description, timestamp=datetime.now()
        )
        self.attachments = []

    @classmethod
    async def create(cls, message: discord.Message, button_cb):
        view = cls(message, button_cb)
        view.status_message = await message.reply(view=view, embed=view.embed)
        return view

    async def submit(self, attachment: bool = False):
        self.embed.title = self.title
        self.embed.description = self.description
        self.embed.timestamp = datetime.now()

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
