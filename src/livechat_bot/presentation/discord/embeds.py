from datetime import datetime
from zoneinfo import ZoneInfo

import discord

from ...domain.enums import JobStatus

STATUS_LABELS = {
    JobStatus.PENDING: "⏳ 等待中", JobStatus.RESOLVING: "🔎 解析中",
    JobStatus.RECORDING: "🔴 錄製中", JobStatus.COMPRESSING: "📦 壓縮中",
    JobStatus.UPLOADING: "📤 上傳中", JobStatus.COMPLETED: "✅ 完成",
    JobStatus.FAILED: "❌ 失敗", JobStatus.CANCELLED: "🚫 已取消",
}


def _timestamp(value: datetime | None) -> str:
    return f"<t:{int(value.timestamp())}:F>" if value else "未知"


def build_job_embed(job, timezone_name: str = "Asia/Taipei") -> discord.Embed:
    embed = discord.Embed(title=STATUS_LABELS[job.status], colour=0x2F80ED)
    title = job.title or "未知"
    value = f"[{title}]({job.youtube_url})" if job.youtube_url else title
    embed.add_field(name="標題", value=value, inline=False)
    channel = job.channel_name or "未知"
    if job.channel_url:
        channel = f"[{channel}]({job.channel_url})"
    embed.add_field(name="YouTube", value=channel, inline=False)
    embed.add_field(name="預計開始時間", value=_timestamp(job.scheduled_start), inline=False)
    if job.finished_at and job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
        embed.add_field(name="結束於", value=_timestamp(job.finished_at), inline=False)
    if job.thumbnail_url:
        embed.set_image(url=job.thumbnail_url)
    try:
        now = datetime.now(ZoneInfo(timezone_name))
    except Exception:
        now = datetime.now().astimezone()
    embed.set_footer(text=f"更新於 {now:%Y-%m-%d %H:%M:%S}")
    if job.error:
        embed.add_field(name="錯誤", value=job.error[:1000], inline=False)
    return embed
