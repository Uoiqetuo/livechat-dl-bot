import zipfile

from pathlib import Path
from app.models.job import Job


class Archiver:
    def archive(
        self,
        job: Job,
        split: bool = False,
        split_size: int = 10 * 1024 * 1024,
        cleanup: bool = False,
    ):
        source_path = job.downloaded_path
        if source_path is None:
            raise ValueError("找不到已下載檔案路徑")

        resolved_source_path = source_path.expanduser().resolve()
        if not resolved_source_path.exists():
            raise FileNotFoundError(f"下載檔案不存在: {resolved_source_path}")

        archive_path = source_path.with_suffix(f"{source_path.suffix}.zip")
        if archive_path.exists():
            archive_path.unlink()

        with zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            archive.write(resolved_source_path, arcname=resolved_source_path.name)

        if split:
            archived_paths: list[Path] = []
            archived_paths = self._split(archive_path, split_size)
            job.archived_paths = archived_paths
        else:
            job.archived_paths = [archive_path]

        if cleanup:
            if job.downloaded_path and job.downloaded_path.exists():
                job.downloaded_path.unlink()

    def _split(self, archive_path: Path, split_size: int) -> list[Path]:
        part_paths: list[Path] = []
        with archive_path.open("rb") as archive_file:
            part_index = 1
            while True:
                chunk = archive_file.read(split_size)
                if not chunk:
                    break

                part_path = archive_path.with_name(
                    f"{archive_path.name}.part{part_index:03d}"
                )
                with part_path.open("wb") as part_file:
                    part_file.write(chunk)
                part_paths.append(part_path)
                part_index += 1
        return part_paths
