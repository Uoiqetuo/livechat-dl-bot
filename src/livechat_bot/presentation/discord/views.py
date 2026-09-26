import discord

from ...domain.enums import JobStatus


class DownloadView(discord.ui.View):
    def __init__(self, job_manager, job, *, timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.job_manager = job_manager
        self.job_id = job.id
        self.owner_id = job.user_id
        self.cancel_button.disabled = not job.status.cancellable

    @discord.ui.button(label="取消錄製", style=discord.ButtonStyle.danger, custom_id="livechat:cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        permissions = getattr(interaction.user, "guild_permissions", None)
        if interaction.user.id != self.owner_id and not getattr(permissions, "administrator", False):
            await interaction.response.send_message("只有建立 Job 的使用者可以取消。", ephemeral=True)
            return
        if await self.job_manager.cancel(self.job_id):
            button.disabled = True
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("此 Job 目前不能取消。", ephemeral=True)
