"""NLRB region lookup, case-to-region assignment, and aggregation.

Pure-Python utilities — no Django dependency. Works with NLRBCaseRecord
dataclasses, dicts, or any object with ``region`` and ``state`` attributes.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

__all__ = [
    'NLRB_REGIONS',
    'STATE_TO_REGIONS',
    'aggregate_by_region',
    'assign_region',
    'lookup_region_by_state',
    'region_summary',
]

# Canonical registry of the 26 regional offices, checked 2026-10-17:
# https://www.nlrb.gov/about-nlrb/who-we-are/regional-offices
# Subregional offices 11 (Winston-Salem), 17 (Kansas City), 24 (San Juan),
# and 26 (Memphis) are not regions and are deliberately excluded.
# The state lists approximate primary coverage using whole states; they are
# neither exhaustive jurisdiction lists nor precise county/sub-state boundaries.
# https://github.com/siege-analytics/siege_utilities/issues/1713 tracks precision.
NLRB_REGIONS: dict[int, dict] = {
    1: {"office": "Boston", "states": ["CT", "MA", "ME", "NH", "RI", "VT"]},
    2: {"office": "New York", "states": ["NY"]},
    3: {"office": "Buffalo", "states": ["NY"]},
    4: {"office": "Philadelphia", "states": ["DE", "PA"]},
    5: {"office": "Baltimore", "states": ["DC", "MD", "VA", "WV"]},
    6: {"office": "Pittsburgh", "states": ["PA", "WV"]},
    7: {"office": "Detroit", "states": ["MI"]},
    8: {"office": "Cleveland", "states": ["OH"]},
    9: {"office": "Cincinnati", "states": ["IN", "KY", "OH"]},
    10: {"office": "Atlanta", "states": ["AL", "GA", "NC", "SC", "TN"]},
    12: {"office": "Tampa", "states": ["FL", "PR", "VI"]},
    13: {"office": "Chicago", "states": ["IL", "IN"]},
    14: {"office": "St. Louis", "states": ["IL", "MO"]},
    15: {"office": "New Orleans", "states": ["AL", "LA", "MS"]},
    16: {"office": "Fort Worth", "states": ["TX"]},
    18: {"office": "Minneapolis", "states": ["MN", "ND", "SD", "WI"]},
    19: {"office": "Seattle", "states": ["AK", "ID", "MT", "OR", "WA", "WY"]},
    # Part of CA and all HI; AS/GU/MP coverage is outside this primary-state list.
    # https://www.nlrb.gov/about-nlrb/who-we-are/regional-offices/region-20-san-francisco
    20: {"office": "San Francisco", "states": ["CA", "HI"]},
    # Much of Southern CA, represented by the whole state for the approximation.
    # https://www.nlrb.gov/about-nlrb/who-we-are/regional-offices/region-21-los-angeles
    21: {"office": "Los Angeles", "states": ["CA"]},
    22: {"office": "Newark", "states": ["NJ"]},
    25: {"office": "Indianapolis", "states": ["IN"]},
    # Also parts of MT/ID/NE, omitted from this primary-state approximation.
    # https://www.nlrb.gov/about-nlrb/who-we-are/regional-offices/region-27-denver
    27: {"office": "Denver", "states": ["CO", "UT", "WY"]},
    # AZ/NM and parts of TX/NV: NV is approximated as a whole state; TX's
    # partial coverage remains outside this primary-state list pending #1713.
    # https://www.nlrb.gov/about-nlrb/who-we-are/regional-offices/region-28-phoenix
    28: {"office": "Phoenix", "states": ["AZ", "NM", "NV"]},
    29: {"office": "Brooklyn", "states": ["NY"]},
    31: {"office": "Los Angeles", "states": ["CA"]},
    # Parts of CA/NV, represented by whole states; precise assignments await #1713.
    # https://www.nlrb.gov/about-nlrb/who-we-are/regional-offices/region-32-oakland
    32: {"office": "Oakland", "states": ["CA", "NV"]},
}


def _build_state_to_regions() -> dict[str, list[int]]:
    state_map: dict[str, list[int]] = defaultdict(list)
    for region_num, info in NLRB_REGIONS.items():
        for state in info["states"]:
            state_map[state].append(region_num)
    return dict(state_map)


STATE_TO_REGIONS: dict[str, list[int]] = _build_state_to_regions()


def lookup_region_by_state(state: str) -> list[int]:
    """Return NLRB region number(s) for a state abbreviation.

    Args:
        state: 2-letter state abbreviation (e.g., 'IL', 'NY').

    Returns:
        List of region numbers. May be >1 for states split across
        multiple regions (e.g., NY → [2, 3, 29]).
        Empty list if state not found.
    """
    return STATE_TO_REGIONS.get(state.upper().strip(), [])


def assign_region(case_record) -> Optional[int]:
    """Assign an NLRB region number to a case record.

    Uses the region number from the case number if available,
    otherwise falls back to state-based lookup (first match).

    Args:
        case_record: Object with ``region`` and ``state`` attributes,
            or a dict with those keys.

    Returns:
        Region number or None if not determinable.
    """
    if isinstance(case_record, dict):
        region = case_record.get("region")
        state = case_record.get("state", "")
    else:
        region = getattr(case_record, "region", None)
        state = getattr(case_record, "state", "")

    if region:
        return int(region)

    if state:
        regions = lookup_region_by_state(state)
        if regions:
            return regions[0]

    return None


def aggregate_by_region(records) -> dict[int, list]:
    """Group records by their NLRB region number.

    Args:
        records: Iterable of case records (dataclass, model, or dict).

    Returns:
        Dict mapping region numbers to lists of records.
        Records without a region are grouped under key 0.
    """
    groups: dict[int, list] = defaultdict(list)
    for record in records:
        region = assign_region(record)
        groups[region or 0].append(record)
    return dict(groups)


def region_summary(records) -> list[dict]:
    """Summarize case counts by region with office names.

    Args:
        records: Iterable of case records.

    Returns:
        List of dicts with keys: region_number, office, case_count.
        Sorted by region_number.
    """
    groups = aggregate_by_region(records)
    summary = []
    for region_num, cases in sorted(groups.items()):
        if region_num == 0:
            summary.append({
                "region_number": 0,
                "office": "Unknown",
                "case_count": len(cases),
            })
        else:
            info = NLRB_REGIONS.get(region_num, {})
            summary.append({
                "region_number": region_num,
                "office": info.get("office", "Unknown"),
                "case_count": len(cases),
            })
    return summary
