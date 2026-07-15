# from yt_dlp import _Params


confs = {
# confs: dict[str, _Params] = {
    "default": {
        "retries": 60,
        "outtmpl": "%(uploader)s/%(release_date,upload_date)s - %(title)s [%(id)s].%(ext)s",
    },
    "chat": {
        "quiet": True,
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
