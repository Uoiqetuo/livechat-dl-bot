import os
import zipfile

import pytest

from livechat_bot.application.archive_service import ArchiveService
from livechat_bot.infrastructure.archive.zip_service import ZipService


@pytest.mark.asyncio
async def test_archive_contains_only_json_and_deletes_source_after_success(tmp_path):
    source = tmp_path / "abc.live_chat.json"
    source.write_text('{"message":"hello"}\n', encoding="utf-8")
    archive = tmp_path / "abc.zip"
    await ArchiveService(ZipService()).create_zip(source, archive)
    assert not source.exists()
    with zipfile.ZipFile(archive) as opened:
        assert opened.namelist() == [source.name]
        assert opened.read(source.name) == b'{"message":"hello"}\n'


@pytest.mark.asyncio
async def test_split_parts_reconstruct_canonical_archive(tmp_path):
    source = tmp_path / "abc.live_chat.json"
    source.write_bytes(os.urandom(10000))
    archive = tmp_path / "abc.zip"
    await ArchiveService(ZipService()).create_zip(source, archive)
    original = archive.read_bytes()
    parts = await ArchiveService(ZipService()).split_archive(archive, 500)
    assert len(parts) > 1
    assert all(part.stat().st_size <= 500 for part in parts)
    assert b"".join(part.read_bytes() for part in parts) == original
