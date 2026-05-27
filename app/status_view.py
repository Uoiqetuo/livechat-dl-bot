import discord
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.task import Task

class StatusView(discord.ui.View):
    def __init__(self, message: discord.Message):
        super().__init__(timeout=None)
        self.message = message
        self.status_message: discord.Message | None = None
        self.task: Task | None = None
        self._show_controls = True
        self.embed = discord.Embed()
        self.embed.title = "成功建立任務"
        self.embed.timestamp = datetime.now()

    @classmethod
    async def create(cls, message: discord.Message):
        view = cls(message)
        view.status_message = await message.reply(view=view, embed=view.embed)
        return view

    def set_task(self, task: "Task"):
        self.task = task

    async def update(self, title: str | None = None, description: str | None = None):
        self.embed.title = title or self.embed.title
        self.embed.description = description or self.embed.description
        if self.status_message is not None:
            await self.status_message.edit(
                embed=self.embed,
                view=self if self._show_controls else None,
            )

    async def hide_controls(self):
        self._show_controls = False
        if self.status_message is not None:
            await self.status_message.edit(embed=self.embed, view=None)

    @discord.ui.button(label="取消", style=discord.ButtonStyle.danger)
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.task is None:
            await interaction.response.send_message("找不到可取消的任務", ephemeral=True)
            return

        cancelled = await self.task.cancel_download()
        button.disabled = True
        await interaction.response.defer()
        if cancelled:
            await self.update("取消中", "正在停止下載，請稍候...")
        else:
            await self.update("任務已結束", "任務已完成或已取消")