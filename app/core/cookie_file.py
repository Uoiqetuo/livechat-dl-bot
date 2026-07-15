import os
import shutil
import tempfile
from pathlib import Path


class CookieFile:
    """Create an isolated temporary copy of a cookies.txt file."""

    def __init__(self, source_path: str | os.PathLike):
        source = Path(source_path)

        if not source.is_file():
            raise FileNotFoundError(source)

        tmp = tempfile.NamedTemporaryFile(
            suffix=source.suffix,
            prefix="cookies_",
            delete=False,
        )
        tmp.close()

        self._path = Path(tmp.name)
        shutil.copy2(source, self._path)

        try:
            os.chmod(self._path, 0o600)
        except PermissionError:
            pass

    @property
    def path(self) -> str:
        """Temporary cookie file path."""
        return str(self._path)

    def get_path(self) -> str:
        return self.path

    def cleanup(self):
        """Delete the temporary cookie file."""
        if self._path and self._path.exists():
            try:
                self._path.unlink()
            except FileNotFoundError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()

    def __del__(self):
        self.cleanup()
