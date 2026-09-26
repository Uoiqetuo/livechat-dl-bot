from pathlib import Path

from ..infrastructure.archive.zip_service import ZipService


class ArchiveService:
    def __init__(self, zip_service: ZipService | None = None):
        self.zip_service = zip_service or ZipService()

    async def create_archive(self, source_file: Path, destination: Path) -> Path:
        result = await self.zip_service.create_zip(source_file, destination)
        source_file.unlink()
        return result

    async def create_zip(self, source_file: Path, destination: Path) -> Path:
        """Compatibility name matching the infrastructure archive contract."""
        return await self.create_archive(source_file, destination)

    async def split_archive(self, archive: Path, max_size: int) -> list[Path]:
        return await self.zip_service.split_archive(archive, max_size)

    async def cleanup_parts(self, parts: list[Path], archive: Path) -> None:
        for part in parts:
            if part != archive:
                part.unlink(missing_ok=True)
