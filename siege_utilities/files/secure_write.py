"""Private text persistence for credentials and configuration exports."""

import os
from pathlib import Path


def _mkdir_private(path: Path) -> None:
    """Create every missing ancestor with owner-only permissions."""
    if not path.exists():
        _mkdir_private(path.parent)
        path.mkdir(mode=0o700, exist_ok=True)


def secure_write_text(path: str | os.PathLike[str], data: str) -> None:
    """Write UTF-8 text with mode 0600 before any payload reaches the file.

    Missing parent directories are created with mode 0700. Existing directories
    are left unchanged; existing files are restricted through the opened fd
    before writing. Final-component symlinks are refused where O_NOFOLLOW is
    available. This is a private write, not an atomic replacement.
    """
    path = Path(path)
    _mkdir_private(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        if hasattr(os, "fchmod"):  # absent on Windows before Python 3.13
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", closefd=False) as stream:
            stream.write(data)
    finally:
        os.close(fd)
