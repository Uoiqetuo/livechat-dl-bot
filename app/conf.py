# from yt_dlp import _Params

from app.runtime_config import POT_BGUTIL_PROVIDER_URL

confs = {
    # confs: dict[str, _Params] = {
    "default": {
        "retries": 60,
        "outtmpl": "%(uploader)s/%(release_date,upload_date)s - %(title)s [%(id)s].%(ext)s",
        "js_runtimes": {
            "deno": {},
            # "node": {},
        },
        "extractor_args": {
            "youtubepot-bgutilhttp": {
                "base_url": [POT_BGUTIL_PROVIDER_URL],
            },
        },
    },
    "chat": {
        "quiet": True,
        # "verbose": True,
        "noprogress": True,
        "skip_download": True,
        "writesubtitles": True,
        "subtitleslangs": ["live_chat"],
        "ignore_no_formats_error": True,
        "nopart": True,
        "retry_sleep_functions": {
            "default": lambda x: 2,
        },
    },
}
