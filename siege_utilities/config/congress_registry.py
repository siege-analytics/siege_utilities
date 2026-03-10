"""
Congress Registry — single source of truth for all congressional metadata.

This module provides congress number ↔ year mappings, chamber types,
party code normalization, and utility functions for working with
United States congressional data.

Data derived from: https://github.com/unitedstates/congress-legislators
"""

from datetime import datetime
from typing import Dict, Optional, Tuple

# ============================================================================
# INTERNAL: current year for dynamic calculation
# ============================================================================
_CURRENT_YEAR = datetime.now().year


# ============================================================================
# CONGRESS NUMBER ↔ YEAR MAPPING
# ============================================================================
# Each congress lasts two years. The 1st Congress convened 1789-03-04.
# Congress N covers years (1787 + 2*N) to (1788 + 2*N).
# Example: 119th Congress = 2025-2026.

def _build_congress_years() -> Dict[int, Tuple[int, int]]:
    """Build mapping of congress number → (start_year, end_year)."""
    result = {}
    for n in range(1, 200):  # generous upper bound
        start = 1787 + 2 * n
        end = 1788 + 2 * n
        result[n] = (start, end)
        if end > _CURRENT_YEAR + 10:
            break
    return result


CONGRESS_YEARS: Dict[int, Tuple[int, int]] = _build_congress_years()
"""Mapping of congress number → (start_year, end_year)."""


# ============================================================================
# CHAMBER TYPES
# ============================================================================

CHAMBER_TYPES: Dict[str, str] = {
    "sen": "Senate",
    "rep": "House of Representatives",
}

CHAMBER_ALIASES: Dict[str, str] = {
    "senate": "sen",
    "house": "rep",
    "house of representatives": "rep",
    "h": "rep",
    "s": "sen",
}


def normalize_chamber(chamber: str) -> str:
    """Normalize a chamber string to canonical form ('sen' or 'rep').

    Accepts: 'sen', 'rep', 'senate', 'house', 'h', 's', etc.
    """
    normalized = chamber.strip().lower()
    if normalized in CHAMBER_TYPES:
        return normalized
    canonical = CHAMBER_ALIASES.get(normalized)
    if canonical:
        return canonical
    raise ValueError(
        f"Unrecognized chamber: '{chamber}'. "
        f"Valid chambers: {sorted(CHAMBER_TYPES.keys())}"
    )


# ============================================================================
# PARTY CODES
# ============================================================================
# Party names as used in unitedstates/congress-legislators data.
# These are full party names, NOT FEC party codes.

PARTY_NAMES: Dict[str, str] = {
    "Republican": "Republican",
    "Democrat": "Democrat",
    "Independent": "Independent",
    "Libertarian": "Libertarian",
    "Green": "Green",
    "Democratic-Farmer-Labor": "Democrat",
    "Progressive": "Progressive",
    "Federalist": "Federalist",
    "Whig": "Whig",
    "Anti-Federalist": "Anti-Federalist",
    "Democratic-Republican": "Democratic-Republican",
    "Free Soil": "Free Soil",
    "Know Nothing": "Know Nothing",
    "Populist": "Populist",
    "Socialist": "Socialist",
    "Farmer-Labor": "Farmer-Labor",
    "Liberal Republican": "Liberal Republican",
    "Nullifier": "Nullifier",
    "Readjuster": "Readjuster",
    "Anti-Jacksonian": "Anti-Jacksonian",
    "Pro-Administration": "Pro-Administration",
    "Anti-Administration": "Anti-Administration",
    "Unionist": "Unionist",
    "Unconditional Unionist": "Unconditional Unionist",
    "Adams": "Adams",
    "Jackson": "Jackson",
    "Crawford": "Crawford",
    "New Progressive": "New Progressive",
    "Popular Democrat": "Popular Democrat",
}

# Map congress-legislators party names to FEC party codes
PARTY_TO_FEC_CODE: Dict[str, str] = {
    "Republican": "REP",
    "Democrat": "DEM",
    "Independent": "IND",
    "Libertarian": "LIB",
    "Green": "GRE",
    "Democratic-Farmer-Labor": "DFL",
    "Progressive": "PRO",
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def congress_for_year(year: int) -> int:
    """Return the congress number that covers the given year.

    Args:
        year: A calendar year (e.g. 2024).

    Returns:
        Congress number (e.g. 118 for 2024).

    Raises:
        ValueError: If year is before 1789 (1st Congress).
    """
    if year < 1789:
        raise ValueError(f"Year {year} is before the 1st Congress (1789)")
    # Congress N starts in year (1787 + 2*N)
    # So N = (year - 1787) // 2, but need to handle boundary
    # A congress starts Jan 3 of odd year, so year 2025 → 119th
    n = (year - 1787) // 2
    # Verify
    start, end = CONGRESS_YEARS.get(n, (0, 0))
    if start <= year <= end:
        return n
    # Try n+1
    start, end = CONGRESS_YEARS.get(n + 1, (0, 0))
    if start <= year <= end:
        return n + 1
    raise ValueError(f"Cannot determine congress for year {year}")


def current_congress() -> int:
    """Return the current congress number."""
    return congress_for_year(_CURRENT_YEAR)


def congress_start_year(congress_number: int) -> int:
    """Return the start year for a given congress number."""
    if congress_number not in CONGRESS_YEARS:
        raise ValueError(f"Unknown congress number: {congress_number}")
    return CONGRESS_YEARS[congress_number][0]


def congress_end_year(congress_number: int) -> int:
    """Return the end year for a given congress number."""
    if congress_number not in CONGRESS_YEARS:
        raise ValueError(f"Unknown congress number: {congress_number}")
    return CONGRESS_YEARS[congress_number][1]


def year_range_for_congress(congress_number: int) -> Tuple[int, int]:
    """Return (start_year, end_year) for a given congress number."""
    if congress_number not in CONGRESS_YEARS:
        raise ValueError(f"Unknown congress number: {congress_number}")
    return CONGRESS_YEARS[congress_number]


def normalize_party(party_name: str) -> str:
    """Normalize a party name from congress-legislators to a canonical form.

    Args:
        party_name: Party name as it appears in the data.

    Returns:
        Canonical party name.
    """
    return PARTY_NAMES.get(party_name, party_name)


def party_to_fec_code(party_name: str) -> Optional[str]:
    """Convert a congress-legislators party name to FEC party code.

    Returns None if no mapping exists.
    """
    return PARTY_TO_FEC_CODE.get(party_name)


# ============================================================================
# STATE CODES (2-letter abbreviations)
# ============================================================================
# Used for validating state codes in legislator data.

VALID_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    # Territories
    "DC", "PR", "GU", "VI", "AS", "MP",
    # Historical
    "DK", "OL", "PI",
}


# ============================================================================
# SENATE CLASSES
# ============================================================================

SENATE_CLASSES = {1, 2, 3}
"""Valid Senate class numbers (determines election cycle rotation)."""
