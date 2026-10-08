import asyncio
from pathlib import Path

import pytest

from livechat_bot.infrastructure.youtube import ytdlp_client as mod
from livechat_bot.infrastructure.youtube.ytdlp_client import YTDLPClient, LiveChatDownloadError


def _write_chat_file(output_dir: Path, video_id: str = "vid") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{video_id}.live_chat.json"
    path.write_text('{"message":"hello"}\n')
    return path


def test_fragment_retries_are_configured(monkeypatch):
    """The live continuation endpoint needs retries; yt-dlp defaults to zero."""
    captured = {}

    class FakeYDL:
        def __init__(self, opts):
            captured.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download):
            _write_chat_file(Path(captured["outtmpl"]).parent)
            return {"id": "vid"}

    monkeypatch.setitem(__import__("sys").modules, "yt_dlp", type("M", (), {"YoutubeDL": FakeYDL}))
    monkeypatch.setattr(mod, "FRAGMENT_RETRIES", 30)

    client = YTDLPClient()
    event = asyncio.Event()
    client._download("https://youtube.com/watch?v=vid", Path("/tmp/x"), event)

    assert captured["fragment_retries"] == 30
    assert captured["retries"] == mod.HTTP_RETRIES
    assert captured["sleep_interval_requests"] == mod.REQUEST_SLEEP_SECONDS


def test_download_is_not_retried_as_a_whole(monkeypatch):
    """A failed live download must surface instead of silently restarting.

    While a stream is live, yt-dlp polls get_live_chat, which returns messages
    from the current moment. Restarting would discard everything recorded so far
    and could succeed while producing a file holding only the last few minutes.
    """
    calls = []

    def fake_download(self, url, output_dir, cancel_event, cookies_file=None):
        calls.append(1)
        raise LiveChatDownloadError("ERROR: Unable to download video subtitles for 'live_chat': HTTP Error 503")

    monkeypatch.setattr(YTDLPClient, "_download", fake_download)

    with pytest.raises(LiveChatDownloadError, match="503"):
        YTDLPClient()._download("https://youtube.com/watch?v=vid", Path("/tmp/nr"), asyncio.Event())

    assert len(calls) == 1


def test_no_whole_download_retry_helper_exists():
    """Guards against reintroducing a whole-download retry wrapper."""
    assert not hasattr(YTDLPClient, "_download_with_retries")
    assert not hasattr(YTDLPClient, "_sleep_unless_cancelled")


def test_proxy_reaches_yt_dlp_options():
    opts = {}
    YTDLPClient("socks5://warp:1080")._apply_shared_options(opts, None)
    assert opts["proxy"] == "socks5://warp:1080"

    # Without a proxy the key must be absent so yt-dlp connects directly.
    plain = {}
    YTDLPClient()._apply_shared_options(plain, None)
    assert "proxy" not in plain


def test_proxy_and_cookies_apply_to_both_yt_dlp_calls():
    """Resolution and download must agree on the proxy, or metadata can be
    fetched through one path while the live chat request uses another."""
    client = YTDLPClient("socks5://warp:1080")

    resolution = {}
    client._apply_shared_options(resolution, Path("/cookies/cookies.txt"))
    download = {}
    client._apply_shared_options(download, Path("/cookies/cookies.txt"))

    assert resolution == download
    assert resolution["proxy"] == "socks5://warp:1080"
    assert resolution["cookiefile"] == "/cookies/cookies.txt"


def test_redacts_credentials_for_logging():
    assert mod._redact_proxy("socks5://warp:1080") == "socks5://warp:1080"
    assert mod._redact_proxy("socks5://bob:s3cr3t@10.0.0.5:1080") == "socks5://***@10.0.0.5:1080"
    assert mod._redact_proxy("http://user@proxy.local") == "http://***@proxy.local"
