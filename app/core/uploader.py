import discord

from app.models.job import Job


class Uploader:
    async def upload(self, job: Job, cleanup: bool = False):
        if job.archived_paths is None:
            raise ValueError("No archived paths found for the job.")

        if job.view is None or job.view.status_message is None:
            raise ValueError("No status message found for the job.")

        for path in job.archived_paths:
            if not path.exists():
                raise FileNotFoundError(f"Archived file not found: {path}")

        job.view.attachments = [
            discord.File(path, filename=path.name) for path in job.archived_paths
        ]
        await job.view.submit(attachment=True)

        if cleanup:
            for path in job.archived_paths:
                if path.exists():
                    path.unlink()
