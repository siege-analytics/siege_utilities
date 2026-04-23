"""NAICS and SOC code crosswalk and normalization.

Maps NLRB industry/occupation codes to Census classification systems:

- **NAICS** (North American Industry Classification System): 2-6 digit
  hierarchical industry codes with revision crosswalks (2012 → 2017 → 2022).
- **SOC** (Standard Occupational Classification): 2-6 digit occupation
  codes with revision crosswalks (2010 → 2018).

Used by the cross-tabulation engine (:mod:`siege_utilities.data.cross_tabulation`)
to join NLRB bargaining-unit data with Census industry/occupation tables.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# NAICS hierarchy
# ---------------------------------------------------------------------------

@dataclass
class NAICSCode:
    """A NAICS industry code with hierarchy metadata."""

    code: str
    title: str
    level: int  # 2=sector, 3=subsector, 4=industry group, 5=industry, 6=national
    parent_code: Optional[str] = None

    @property
    def sector(self) -> str:
        """2-digit sector code."""
        return self.code[:2]


# NAICS sector definitions (2-digit)
NAICS_SECTORS: dict[str, str] = {
    "11": "Agriculture, Forestry, Fishing and Hunting",
    "21": "Mining, Quarrying, and Oil and Gas Extraction",
    "22": "Utilities",
    "23": "Construction",
    "31": "Manufacturing",
    "32": "Manufacturing",
    "33": "Manufacturing",
    "42": "Wholesale Trade",
    "44": "Retail Trade",
    "45": "Retail Trade",
    "48": "Transportation and Warehousing",
    "49": "Transportation and Warehousing",
    "51": "Information",
    "52": "Finance and Insurance",
    "53": "Real Estate and Rental and Leasing",
    "54": "Professional, Scientific, and Technical Services",
    "55": "Management of Companies and Enterprises",
    "56": "Administrative and Support and Waste Management",
    "61": "Educational Services",
    "62": "Health Care and Social Assistance",
    "71": "Arts, Entertainment, and Recreation",
    "72": "Accommodation and Food Services",
    "81": "Other Services (except Public Administration)",
    "92": "Public Administration",
}


def parse_naics(code: str) -> NAICSCode:
    """Parse a NAICS code string into a :class:`NAICSCode`.

    Parameters
    ----------
    code : str
        2-6 digit NAICS code.

    Returns
    -------
    NAICSCode

    Raises
    ------
    ValueError
        If the code is not 2-6 digits.
    """
    code = code.strip()
    if not re.match(r"^\d{2,6}$", code):
        raise ValueError(f"Invalid NAICS code (must be 2-6 digits): {code!r}")

    level = len(code)
    parent = code[: level - 1] if level > 2 else None
    sector_code = code[:2]
    title = NAICS_SECTORS.get(sector_code, "Unknown Sector")

    return NAICSCode(code=code, title=title, level=level, parent_code=parent)


def naics_ancestors(code: str) -> list[str]:
    """Return ancestor codes from sector down to the given code.

    >>> naics_ancestors("541511")
    ['54', '541', '5415', '54151', '541511']
    """
    code = code.strip()
    return [code[: i] for i in range(2, len(code) + 1)]


def naics_to_sector(code: str) -> tuple[str, str]:
    """Return (sector_code, sector_title) for any NAICS code."""
    sector = code.strip()[:2]
    return sector, NAICS_SECTORS.get(sector, "Unknown Sector")


# ---------------------------------------------------------------------------
# NAICS revision crosswalks
# ---------------------------------------------------------------------------

# Major 2017→2022 changes (selected high-impact mappings)
_NAICS_2017_TO_2022: dict[str, list[str]] = {
    "454110": ["455110"],  # Electronic Shopping → Electronic Shopping and Mail-Order
    "519130": ["519290"],  # Internet Publishing → Web Search Portals etc.
    "517311": ["517111"],  # Wired Telecommunications → Wired and Wireless Telecom
    "517312": ["517111"],  # Wireless Telecommunications → merged
    "423990": ["423990"],  # Durable goods (unchanged)
}

# Major 2012→2017 changes
_NAICS_2012_TO_2017: dict[str, list[str]] = {
    "519130": ["519130"],  # Unchanged in this revision
    "517110": ["517311"],  # Wired Telecom → split
}


def crosswalk_naics(
    code: str,
    from_year: int = 2017,
    to_year: int = 2022,
) -> list[str]:
    """Map a NAICS code from one revision to another.

    Parameters
    ----------
    code : str
        Source NAICS code.
    from_year : int
        Source revision year (2012 or 2017).
    to_year : int
        Target revision year (2017 or 2022).

    Returns
    -------
    list of str
        Target code(s). May be >1 if the source was split.
        Returns ``[code]`` if no mapping is found (assumed unchanged).
    """
    code = code.strip()
    if from_year == 2017 and to_year == 2022:
        return _NAICS_2017_TO_2022.get(code, [code])
    if from_year == 2012 and to_year == 2017:
        return _NAICS_2012_TO_2017.get(code, [code])
    if from_year == 2012 and to_year == 2022:
        intermediate = crosswalk_naics(code, 2012, 2017)
        result = []
        for c in intermediate:
            result.extend(crosswalk_naics(c, 2017, 2022))
        return result
    raise ValueError(f"Unsupported crosswalk: {from_year} → {to_year}")


# ---------------------------------------------------------------------------
# SOC codes
# ---------------------------------------------------------------------------

@dataclass
class SOCCode:
    """A Standard Occupational Classification code."""

    code: str
    title: str
    level: str  # "major", "minor", "broad", "detailed"

    @property
    def major_group(self) -> str:
        """2-digit major group (e.g., "11" from "11-1011")."""
        return self.code.split("-")[0] if "-" in self.code else self.code[:2]


SOC_MAJOR_GROUPS: dict[str, str] = {
    "11": "Management",
    "13": "Business and Financial Operations",
    "15": "Computer and Mathematical",
    "17": "Architecture and Engineering",
    "19": "Life, Physical, and Social Science",
    "21": "Community and Social Service",
    "23": "Legal",
    "25": "Educational Instruction and Library",
    "27": "Arts, Design, Entertainment, Sports, and Media",
    "29": "Healthcare Practitioners and Technical",
    "31": "Healthcare Support",
    "33": "Protective Service",
    "35": "Food Preparation and Serving Related",
    "37": "Building and Grounds Cleaning and Maintenance",
    "39": "Personal Care and Service",
    "41": "Sales and Related",
    "43": "Office and Administrative Support",
    "45": "Farming, Fishing, and Forestry",
    "47": "Construction and Extraction",
    "49": "Installation, Maintenance, and Repair",
    "51": "Production",
    "53": "Transportation and Material Moving",
    "55": "Military Specific",
}


def parse_soc(code: str) -> SOCCode:
    """Parse an SOC code string.

    Parameters
    ----------
    code : str
        SOC code in ``"XX-XXXX"`` format or just the major group ``"XX"``.

    Returns
    -------
    SOCCode
    """
    code = code.strip()
    if re.match(r"^\d{2}$", code):
        return SOCCode(code=code, title=SOC_MAJOR_GROUPS.get(code, "Unknown"), level="major")
    if not re.match(r"^\d{2}-\d{4}$", code):
        raise ValueError(f"Invalid SOC code (expected XX-XXXX): {code!r}")

    major = code[:2]
    minor_digits = code.split("-")[1]
    if minor_digits.endswith("0"):
        level = "broad"
    else:
        level = "detailed"
    if minor_digits == "0000":
        level = "major"

    return SOCCode(
        code=code,
        title=SOC_MAJOR_GROUPS.get(major, "Unknown"),
        level=level,
    )


def soc_to_major_group(code: str) -> tuple[str, str]:
    """Return (major_code, title) for any SOC code."""
    major = code.strip().split("-")[0][:2]
    return major, SOC_MAJOR_GROUPS.get(major, "Unknown")


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def fuzzy_match_naics(
    text: str,
    candidates: Optional[dict[str, str]] = None,
    threshold: float = 0.5,
) -> list[tuple[str, str, float]]:
    """Simple token-overlap fuzzy match of *text* against NAICS sector titles.

    Parameters
    ----------
    text : str
        Free-text industry description (e.g., from NLRB filings).
    candidates : dict, optional
        ``{code: title}`` mapping.  Defaults to :data:`NAICS_SECTORS`.
    threshold : float
        Minimum similarity score (0-1) to include.

    Returns
    -------
    list of (code, title, score)
        Sorted by score descending.
    """
    if candidates is None:
        candidates = NAICS_SECTORS

    text_tokens = set(text.lower().split())
    results = []
    for code, title in candidates.items():
        title_tokens = set(title.lower().split())
        if not title_tokens:
            continue
        overlap = len(text_tokens & title_tokens)
        score = overlap / max(len(text_tokens), len(title_tokens))
        if score >= threshold:
            results.append((code, title, round(score, 3)))

    results.sort(key=lambda x: x[2], reverse=True)
    return results
