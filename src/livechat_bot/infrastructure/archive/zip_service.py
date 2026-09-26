import asyncio
import zipfile
from pathlib import Path


class ArchiveError(RuntimeError):
    pass


class ArchiveSplitError(RuntimeError):
    pass


class ZipService:
    async def create_zip(self, source_file: Path, destination: Path) -> Path:
        return await asyncio.to_thread(self._create_zip, Path(source_file), Path(destination))

    def _create_zip(self, source_file: Path, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_suffix(destination.suffix + ".creating")
        try:
            with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(source_file, arcname=source_file.name)
            with zipfile.ZipFile(temp) as archive:
                names = archive.namelist()
                if names != [source_file.name] or archive.testzip() is not None:
                    raise ArchiveError("created archive failed validation")
            temp.replace(destination)
            return destination
        except Exception as exc:
            temp.unlink(missing_ok=True)
            if isinstance(exc, ArchiveError):
                raise
            raise ArchiveError(str(exc)) from exc

    async def split_archive(self, archive: Path, max_size: int) -> list[Path]:
        return await asyncio.to_thread(self._split_archive, Path(archive), max_size)

    def _split_archive(self, archive: Path, max_size: int) -> list[Path]:
        if max_size <= 0:
            raise ArchiveSplitError("max part size must be positive")
        data = archive.read_bytes()
        if len(data) <= max_size:
            return [archive]
        parts: list[Path] = []
        for index, offset in enumerate(range(0, len(data), max_size), 1):
            part = archive.with_name(f"{archive.stem}.part{index:02d}{archive.suffix}")
            part.write_bytes(data[offset:offset + max_size])
            parts.append(part)
        if any(part.stat().st_size > max_size for part in parts):
            raise ArchiveSplitError("part exceeds configured size")
        return parts
