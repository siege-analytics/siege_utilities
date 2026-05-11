"""Cache helpers — on-disk caching for sample datasets used by notebooks.

The notebooks under ``notebooks/`` deliberately do not commit spatial or
large tabular fixtures to the repo. Instead, each notebook that needs a
dataset calls :func:`ensure_sample_dataset`, which downloads the file on
first run into a user-scoped cache directory and returns a local path on
every subsequent run.

Default cache root: ``~/.cache/siege_utilities/notebooks/``. Override per
call via the ``cache_dir`` argument or globally with the
``SIEGE_UTILITIES_CACHE_DIR`` environment variable.

The cache enforces a per-call size budget — when adding a new file would
exceed the budget, oldest-access entries are evicted first (LRU by
``st_atime``). Default budget: 5 GiB; override via the
``SIEGE_UTILITIES_CACHE_MAX_BYTES`` env var or the ``max_bytes`` kwarg.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# 5 GiB default cap. Notebooks pull state-level shapefiles (~50-150 MiB
# each) and the occasional national TIGER set (>1 GiB), so 5 GiB allows
# a working set of a dozen-ish national fixtures or many state-level
# ones without churn. Override per env-var for CI/space-constrained
# environments.
_DEFAULT_MAX_BYTES = 5 * 1024 * 1024 * 1024


class SampleDatasetError(RuntimeError):
    """Raised when a sample dataset cannot be fetched or fails verification."""


def _default_cache_dir() -> Path:
    override = os.environ.get("SIEGE_UTILITIES_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cache" / "siege_utilities" / "notebooks"


def _cache_budget_bytes() -> int:
    raw = os.environ.get("SIEGE_UTILITIES_CACHE_MAX_BYTES")
    if not raw:
        return _DEFAULT_MAX_BYTES
    try:
        return max(int(raw), 0)
    except ValueError:
        log.warning("SIEGE_UTILITIES_CACHE_MAX_BYTES=%r is not an int; using default.", raw)
        return _DEFAULT_MAX_BYTES


def _evict_to_fit(root: Path, incoming_bytes: int, budget: int) -> None:
    """LRU-evict from *root* until total size + incoming_bytes <= budget.

    Oldest-access first (``st_atime``); ties broken by ``st_mtime``.
    Files actively in use by another process will fail to unlink on
    Windows; we log and skip rather than abort eviction.
    """
    if budget <= 0:
        return
    entries = []
    total = 0
    for p in root.iterdir():
        if not p.is_file():
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        entries.append((st.st_atime, st.st_mtime, st.st_size, p))
        total += st.st_size
    if total + incoming_bytes <= budget:
        return
    # Sort oldest-access first.
    entries.sort()
    for atime, mtime, size, p in entries:
        if total + incoming_bytes <= budget:
            break
        try:
            p.unlink()
            total -= size
            log.info("cache: evicted %s (%d bytes, last access %s)", p.name, size, atime)
        except OSError as e:
            log.warning("cache: could not evict %s: %s", p, e)


def ensure_sample_dataset(
    name: str,
    url: str,
    *,
    cache_dir: Optional[Path] = None,
    sha256: Optional[str] = None,
    max_bytes: Optional[int] = None,
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
        # Touch atime so the LRU eviction order reflects use, not just
        # initial download time.
        try:
            os.utime(target, None)
        except OSError:
            pass
        return target

    # Atomic write: download into a per-call temp file with mkstemp,
    # fsync, then os.replace into place. The previous predictable
    # `.part` suffix had a TOCTOU race when two callers downloaded the
    # same dataset concurrently — the second writer could clobber the
    # first's partial.
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=f".{name}.",
        suffix=".part",
        dir=str(root),
    )
    tmp = Path(tmp_path_str)
    try:
        try:
            with os.fdopen(fd, "wb") as f, urllib.request.urlopen(url) as resp:
                while chunk := resp.read(1 << 16):
                    f.write(chunk)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
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
                raise SampleDatasetError(
                    f"sha256 mismatch for {name!r}: expected {sha256}, got {got}"
                )

        # Enforce the size budget BEFORE moving into place so a giant
        # download can't temporarily blow past the cap.
        size = tmp.stat().st_size
        budget = max_bytes if max_bytes is not None else _cache_budget_bytes()
        _evict_to_fit(root, size, budget)

        os.replace(tmp, target)
        return target
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
