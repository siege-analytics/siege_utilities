"""Cache helpers — on-disk caching for sample datasets used by notebooks.

The notebooks under ``notebooks/`` deliberately do not commit spatial or
large tabular fixtures to the repo. Instead, each notebook that needs a
dataset calls :func:`ensure_sample_dataset`, which downloads the file on
first run into a user-scoped cache directory and returns a local path on
every subsequent run.

Default cache root: ``~/.cache/siege_utilities/notebooks/``. Override per
call via the ``cache_dir`` argument or globally with the
``SIEGE_UTILITIES_CACHE_DIR`` environment variable.
"""

from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path
from typing import Optional


class SampleDatasetError(RuntimeError):
    """Raised when a sample dataset cannot be fetched or fails verification."""


def _default_cache_dir() -> Path:
    override = os.environ.get("SIEGE_UTILITIES_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cache" / "siege_utilities" / "notebooks"


def ensure_sample_dataset(
    name: str,
    url: str,
    *,
    cache_dir: Optional[Path] = None,
    sha256: Optional[str] = None,
) -> Path:
    """Return a local path to ``name``, downloading from ``url`` on first use.

    Parameters
    ----------
    name:
        Filename to use in the cache (e.g. ``"tx_counties_2020.geojson"``).
        Not treated as a directory — must be a single filename. Cache
        layout is flat by design; if you need hierarchy, encode it in the
        name.
    url:
        HTTPS URL to download from on cache miss.
    cache_dir:
        Override the cache directory. Defaults to
        :func:`_default_cache_dir` (``~/.cache/siege_utilities/notebooks``
        or the value of ``SIEGE_UTILITIES_CACHE_DIR``).
    sha256:
        Optional hex digest. When provided, a freshly-downloaded file is
        verified against it and :class:`SampleDatasetError` is raised on
        mismatch (the corrupt file is removed).

    Returns
    -------
    Path
        Absolute path to the cached file.

    Raises
    ------
    SampleDatasetError
        On HTTP failure or SHA-256 mismatch.
    ValueError
        If ``name`` contains a path separator.
    """
    if "/" in name or os.sep in name:
        raise ValueError(
            f"name {name!r} must be a single filename, not a path"
        )

    root = (cache_dir or _default_cache_dir()).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    target = root / name

    if target.exists():
        return target

    tmp = target.with_suffix(target.suffix + ".part")
    try:
        with urllib.request.urlopen(url) as resp, open(tmp, "wb") as f:
            while chunk := resp.read(1 << 16):
                f.write(chunk)
    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        raise SampleDatasetError(
            f"failed to download sample dataset {name!r} from {url}: {e}"
        ) from e

    if sha256 is not None:
        h = hashlib.sha256()
        with open(tmp, "rb") as f:
            while chunk := f.read(1 << 16):
                h.update(chunk)
        got = h.hexdigest()
        if got != sha256.lower():
            tmp.unlink()
            raise SampleDatasetError(
                f"sha256 mismatch for {name!r}: expected {sha256}, got {got}"
            )

    tmp.rename(target)
    return target
