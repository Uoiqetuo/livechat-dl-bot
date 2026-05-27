from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import zipfile


DEFAULT_SPLIT_SIZE = 10 * 1024 * 1024


@dataclass(slots=True)
class ArchiveSplitResult:
    archive_path: Path
    part_paths: list[Path]


def build_archive_and_split(source_path: Path, split_size: int = DEFAULT_SPLIT_SIZE) -> ArchiveSplitResult:
    source_path = source_path.expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"找不到下載檔案: {source_path}")
    if source_path.is_dir():
        raise IsADirectoryError(f"不能壓縮資料夾: {source_path}")

    archive_path = source_path.with_suffix(f"{source_path.suffix}.zip")
    if archive_path.exists():
        archive_path.unlink()

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(source_path, arcname=source_path.name)

    part_paths: list[Path] = []
    with archive_path.open("rb") as archive_file:
        part_index = 1
        while True:
            chunk = archive_file.read(split_size)
            if not chunk:
                break

            part_path = archive_path.with_name(f"{archive_path.name}.part{part_index:03d}")
            with part_path.open("wb") as part_file:
                part_file.write(chunk)
            part_paths.append(part_path)
            part_index += 1

    return ArchiveSplitResult(archive_path=archive_path, part_paths=part_paths)


def cleanup_paths(*paths: Path) -> None:
    for path in paths:
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        except FileNotFoundError:
            continue