"""Private text persistence for credentials and configuration exports."""

import logging
import os
from pathlib import Path
import tempfile


def _mkdir_private(path: Path) -> None:
    """Create every missing ancestor with owner-only permissions."""
    if not path.exists():
        _mkdir_private(path.parent)
        path.mkdir(mode=0o700, exist_ok=True)


def secure_write_text(path: str | os.PathLike[str], data: str) -> None:
    """Atomically replace UTF-8 text using a private mode-0600 sibling file.

    Missing parent directories are created with mode 0700. Existing directories
    are left unchanged. Failed writes leave the existing file and its mode
    intact. Final-component symlinks are replaced without following them.
    Sync the file before replacement and the directory afterward where supported.
    """
    path = Path(path)
    _mkdir_private(path.parent)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        try:
            if hasattr(os, "fchmod"):  # absent on Windows before Python 3.13
                os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8", closefd=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    # The replacement has committed; directory syncing is best effort on
    # platforms/filesystems that do not support it.
    if os.name == "posix":
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            logging.getLogger(__name__).debug(
                "Directory fsync unavailable for %s", path.parent, exc_info=True,
            )
