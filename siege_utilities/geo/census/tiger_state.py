"""Last-fetched-vintage state tracking for Census TIGER pulls.

Supports cron-friendly "is there a new vintage published?" checks. The
state file holds a single integer (the year most recently downloaded).

Usage::

    from pathlib import Path
    from siege_utilities.geo.census.tiger_state import check_for_updates

    state = Path('/var/lib/sw/tiger.year')
    has_update, latest = check_for_updates(state)
    if has_update:
        # download via CensusTIGERProvider.get_boundary(...)
        set_last_fetched_vintage(state, latest)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


def get_last_fetched_vintage(state_file: Path) -> Optional[int]:
    """Read the last-fetched vintage year from `state_file`.

    Returns None when the file is absent or unparseable.
    """
    if not state_file.exists():
        return None
    try:
        return int(state_file.read_text().strip())
    except (ValueError, OSError):
        return None


def set_last_fetched_vintage(state_file: Path, year: int) -> None:
    """Write `year` to `state_file`. Creates parent dirs if needed."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(f"{int(year)}\n")


def check_for_updates(
    state_file: Path,
    *,
    provider=None,
) -> tuple[bool, Optional[int]]:
    """Return (has_update, latest_year).

    `has_update` is True when the latest published vintage is greater
    than the recorded last-fetched year, OR when no state file exists.
    Returns (False, None) when discovery fails (offline / endpoint down).

    `provider` defaults to a fresh `CensusTIGERProvider`; pass a
    pre-built one to share session state or to inject a test double.
    """
    if provider is None:
        from siege_utilities.geo.providers.boundary_providers import CensusTIGERProvider
        provider = CensusTIGERProvider()

    latest = provider.latest_vintage()
    if latest is None:
        return False, None

    last = get_last_fetched_vintage(state_file)
    if last is None:
        return True, latest
    return latest > last, latest
