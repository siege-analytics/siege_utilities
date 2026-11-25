"""Home lookup shared by lazy configuration defaults.

An unmapped POSIX uid uses ``<tempdir>/siege_utilities-<uid>`` as its
home substitute. On Windows the substitute is ``<tempdir>/siege_utilities``.
These helpers only resolve paths; they do not create directories.
"""

import os
from pathlib import Path
import tempfile


def _fallback_home_directory() -> Path:
    suffix = f"-{os.getuid()}" if hasattr(os, "getuid") else ""
    return Path(tempfile.gettempdir()) / f"siege_utilities{suffix}"


def _home_directory() -> Path:
    """Return the home directory, or a temporary substitute if unavailable."""
    try:
        return Path.home()
    except (RuntimeError, KeyError):
        return _fallback_home_directory()
