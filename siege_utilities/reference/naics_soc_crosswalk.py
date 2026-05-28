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


# ---------------------------------------------------------------------------
# Bundled NAICS subsector / industry group codes (3-4 digit)
# ---------------------------------------------------------------------------

NAICS_SUBSECTORS: dict[str, str] = {
    "111": "Crop Production",
    "112": "Animal Production and Aquaculture",
    "113": "Forestry and Logging",
    "114": "Fishing, Hunting and Trapping",
    "115": "Support Activities for Agriculture and Forestry",
    "211": "Oil and Gas Extraction",
    "212": "Mining (except Oil and Gas)",
    "213": "Support Activities for Mining",
    "221": "Utilities",
    "236": "Construction of Buildings",
    "237": "Heavy and Civil Engineering Construction",
    "238": "Specialty Trade Contractors",
    "311": "Food Manufacturing",
    "312": "Beverage and Tobacco Product Manufacturing",
    "313": "Textile Mills",
    "314": "Textile Product Mills",
    "315": "Apparel Manufacturing",
    "316": "Leather and Allied Product Manufacturing",
    "321": "Wood Product Manufacturing",
    "322": "Paper Manufacturing",
    "323": "Printing and Related Support Activities",
    "324": "Petroleum and Coal Products Manufacturing",
    "325": "Chemical Manufacturing",
    "326": "Plastics and Rubber Products Manufacturing",
    "327": "Nonmetallic Mineral Product Manufacturing",
    "331": "Primary Metal Manufacturing",
    "332": "Fabricated Metal Product Manufacturing",
    "333": "Machinery Manufacturing",
    "334": "Computer and Electronic Product Manufacturing",
    "335": "Electrical Equipment, Appliance, and Component Manufacturing",
    "336": "Transportation Equipment Manufacturing",
    "337": "Furniture and Related Product Manufacturing",
    "339": "Miscellaneous Manufacturing",
    "423": "Merchant Wholesalers, Durable Goods",
    "424": "Merchant Wholesalers, Nondurable Goods",
    "425": "Wholesale Trade Agents and Brokers",
    "441": "Motor Vehicle and Parts Dealers",
    "442": "Furniture and Home Furnishings Retailers",
    "443": "Electronics and Appliance Retailers",
    "444": "Building Material and Garden Equipment Retailers",
    "445": "Food and Beverage Retailers",
    "446": "Health and Personal Care Retailers",
    "447": "Gasoline Stations",
    "448": "Clothing and Clothing Accessories Retailers",
    "449": "Furniture, Home Furnishings, Electronics, and Appliance Retailers",
    "451": "Sporting Goods, Hobby, Musical Instrument, and Book Retailers",
    "452": "General Merchandise Retailers",
    "453": "Miscellaneous Store Retailers",
    "454": "Nonstore Retailers",
    "455": "General Merchandise Retailers (2022)",
    "456": "Health and Personal Care Retailers (2022)",
    "481": "Air Transportation",
    "482": "Rail Transportation",
    "483": "Water Transportation",
    "484": "Truck Transportation",
    "485": "Transit and Ground Passenger Transportation",
    "486": "Pipeline Transportation",
    "487": "Scenic and Sightseeing Transportation",
    "488": "Support Activities for Transportation",
    "491": "Postal Service",
    "492": "Couriers and Messengers",
    "493": "Warehousing and Storage",
    "511": "Publishing Industries",
    "512": "Motion Picture and Sound Recording Industries",
    "515": "Broadcasting (except Internet)",
    "516": "Internet Publishing and Broadcasting",
    "517": "Telecommunications",
    "518": "Computing Infrastructure Providers, Data Processing, and Related Services",
    "519": "Web Search Portals, Libraries, Archives, and Other Information Services",
    "521": "Monetary Authorities—Central Bank",
    "522": "Credit Intermediation and Related Activities",
    "523": "Securities, Commodity Contracts, and Other Financial Investments",
    "524": "Insurance Carriers and Related Activities",
    "525": "Funds, Trusts, and Other Financial Vehicles",
    "531": "Real Estate",
    "532": "Rental and Leasing Services",
    "533": "Lessors of Nonfinancial Intangible Assets",
    "541": "Professional, Scientific, and Technical Services",
    "551": "Management of Companies and Enterprises",
    "561": "Administrative and Support Services",
    "562": "Waste Management and Remediation Services",
    "611": "Educational Services",
    "621": "Ambulatory Health Care Services",
    "622": "Hospitals",
    "623": "Nursing and Residential Care Facilities",
    "624": "Social Assistance",
    "711": "Performing Arts, Spectator Sports, and Related Industries",
    "712": "Museums, Historical Sites, and Similar Institutions",
    "713": "Amusement, Gambling, and Recreation Industries",
    "721": "Accommodation",
    "722": "Food Services and Drinking Places",
    "811": "Repair and Maintenance",
    "812": "Personal and Laundry Services",
    "813": "Religious, Grantmaking, Civic, Professional, and Similar Organizations",
    "814": "Private Households",
    "921": "Executive, Legislative, and Other General Government Support",
    "922": "Justice, Public Order, and Safety Activities",
    "923": "Administration of Human Resource Programs",
    "924": "Administration of Environmental Quality Programs",
    "925": "Administration of Housing, Urban Planning, and Community Development",
    "926": "Administration of Economic Programs",
    "927": "Space Research and Technology",
    "928": "National Security and International Affairs",
}


# ---------------------------------------------------------------------------
# Bundled SOC minor / broad occupation codes
# ---------------------------------------------------------------------------

SOC_MINOR_GROUPS: dict[str, str] = {
    "11-1000": "Top Executives",
    "11-2000": "Advertising, Marketing, Promotions, Public Relations, and Sales Managers",
    "11-3000": "Operations Specialties Managers",
    "11-9000": "Other Management Occupations",
    "13-1000": "Business Operations Specialists",
    "13-2000": "Financial Specialists",
    "15-1200": "Computer Occupations",
    "15-2000": "Mathematical Science Occupations",
    "17-1000": "Architects, Surveyors, and Cartographers",
    "17-2000": "Engineers",
    "17-3000": "Drafters, Engineering Technicians, and Mapping Technicians",
    "19-1000": "Life Scientists",
    "19-2000": "Physical Scientists",
    "19-3000": "Social Scientists and Related Workers",
    "19-4000": "Life, Physical, and Social Science Technicians",
    "21-1000": "Counselors, Social Workers, and Other Community and Social Service Specialists",
    "23-1000": "Lawyers, Judges, and Related Workers",
    "23-2000": "Legal Support Workers",
    "25-1000": "Postsecondary Teachers",
    "25-2000": "Preschool, Elementary, Middle, Secondary, and Special Education Teachers",
    "25-3000": "Other Teachers and Instructors",
    "25-4000": "Librarians, Curators, and Archivists",
    "25-9000": "Other Educational Instruction and Library Occupations",
    "27-1000": "Art and Design Workers",
    "27-2000": "Entertainers and Performers, Sports and Related Workers",
    "27-3000": "Media and Communication Workers",
    "27-4000": "Media and Communication Equipment Workers",
    "29-1000": "Healthcare Diagnosing or Treating Practitioners",
    "29-2000": "Health Technologists and Technicians",
    "29-9000": "Other Healthcare Practitioners and Technical Occupations",
    "31-1100": "Home Health and Personal Care Aides; and Nursing Assistants",
    "31-2000": "Occupational Therapy and Physical Therapist Assistants and Aides",
    "31-9000": "Other Healthcare Support Occupations",
    "33-1000": "First-Line Supervisors of Protective Service Workers",
    "33-2000": "Firefighting and Prevention Workers",
    "33-3000": "Law Enforcement Workers",
    "33-9000": "Other Protective Service Workers",
    "35-1000": "Supervisors of Food Preparation and Serving Workers",
    "35-2000": "Cooks and Food Preparation Workers",
    "35-3000": "Food and Beverage Serving Workers",
    "35-9000": "Other Food Preparation and Serving Related Workers",
    "37-1000": "Supervisors of Building and Grounds Cleaning and Maintenance Workers",
    "37-2000": "Building Cleaning and Pest Control Workers",
    "37-3000": "Grounds Maintenance Workers",
    "39-1000": "Supervisors of Personal Care and Service Workers",
    "39-2000": "Animal Care and Service Workers",
    "39-3000": "Entertainment Attendants and Related Workers",
    "39-4000": "Funeral Service Workers",
    "39-5000": "Personal Appearance Workers",
    "39-9000": "Other Personal Care and Service Workers",
    "41-1000": "Supervisors of Sales Workers",
    "41-2000": "Retail Sales Workers",
    "41-3000": "Sales Representatives, Services",
    "41-4000": "Sales Representatives, Wholesale and Manufacturing",
    "41-9000": "Other Sales and Related Workers",
    "43-1000": "Supervisors of Office and Administrative Support Workers",
    "43-2000": "Communications Equipment Operators",
    "43-3000": "Financial Clerks",
    "43-4000": "Information and Record Clerks",
    "43-5000": "Material Recording, Scheduling, Dispatching, and Distributing Workers",
    "43-6000": "Secretaries and Administrative Assistants",
    "43-9000": "Other Office and Administrative Support Workers",
    "45-1000": "Supervisors of Farming, Fishing, and Forestry Workers",
    "45-2000": "Agricultural Workers",
    "45-3000": "Fishing and Hunting Workers",
    "45-4000": "Forest, Conservation, and Logging Workers",
    "47-1000": "Supervisors of Construction and Extraction Workers",
    "47-2000": "Construction Trades Workers",
    "47-3000": "Helpers, Construction Trades",
    "47-4000": "Other Construction and Related Workers",
    "47-5000": "Extraction Workers",
    "49-1000": "Supervisors of Installation, Maintenance, and Repair Workers",
    "49-2000": "Electrical and Electronic Equipment Mechanics, Installers, and Repairers",
    "49-3000": "Vehicle and Mobile Equipment Mechanics, Installers, and Repairers",
    "49-9000": "Other Installation, Maintenance, and Repair Occupations",
    "51-1000": "Supervisors of Production Workers",
    "51-2000": "Assemblers and Fabricators",
    "51-3000": "Food Processing Workers",
    "51-4000": "Metal Workers and Plastic Workers",
    "51-5100": "Printing Workers",
    "51-6000": "Textile, Apparel, and Furnishings Workers",
    "51-7000": "Woodworkers",
    "51-8000": "Plant and System Operators",
    "51-9000": "Other Production Occupations",
    "53-1000": "Supervisors of Transportation and Material Moving Workers",
    "53-2000": "Air Transportation Workers",
    "53-3000": "Motor Vehicle Operators",
    "53-4000": "Rail Transportation Workers",
    "53-5000": "Water Transportation Workers",
    "53-6000": "Other Transportation Workers",
    "53-7000": "Material Moving Workers",
    "55-1000": "Military Officer Special and Tactical Operations Leaders",
    "55-2000": "First-Line Enlisted Military Supervisors",
    "55-3000": "Military Enlisted Tactical Operations and Air/Weapons Specialists",
}


# ---------------------------------------------------------------------------
# Combined lookup tables
# ---------------------------------------------------------------------------

def get_naics_lookup() -> dict[str, str]:
    """Return a combined NAICS lookup table (sectors + subsectors).

    Returns:
        Dict mapping NAICS codes to titles at all available levels.
    """
    combined = {}
    combined.update(NAICS_SECTORS)
    combined.update(NAICS_SUBSECTORS)
    return combined


def get_soc_lookup() -> dict[str, str]:
    """Return a combined SOC lookup table (major groups + minor groups).

    Returns:
        Dict mapping SOC codes to titles at all available levels.
    """
    combined = {}
    combined.update(SOC_MAJOR_GROUPS)
    combined.update(SOC_MINOR_GROUPS)
    return combined


def naics_title(code: str) -> str:
    """Look up the title for a NAICS code at any level.

    Checks subsector-level first, then falls back to sector.
    Returns 'Unknown' if not found.
    """
    code = code.strip()
    lookup = get_naics_lookup()
    if code in lookup:
        return lookup[code]
    sector = code[:2]
    if sector in NAICS_SECTORS:
        return NAICS_SECTORS[sector]
    return "Unknown"


def soc_title(code: str) -> str:
    """Look up the title for an SOC code at any level.

    Checks minor-group level first, then falls back to major group.
    Returns 'Unknown' if not found.
    """
    code = code.strip()
    lookup = get_soc_lookup()
    if code in lookup:
        return lookup[code]
    major = code.split("-")[0][:2]
    if major in SOC_MAJOR_GROUPS:
        return SOC_MAJOR_GROUPS[major]
    return "Unknown"


# ---------------------------------------------------------------------------
# Query interface — filter NLRB records by NAICS prefix
# ---------------------------------------------------------------------------

def filter_by_naics(records, naics_prefix: str) -> list:
    """Filter NLRB case records by NAICS code prefix.

    Works with any iterable of objects that have a ``naics_code`` attribute
    (NLRBCaseRecord, NLRBCase model instances, or dicts with 'naics_code').

    Args:
        records: Iterable of records to filter.
        naics_prefix: NAICS prefix to match (e.g., '622' for hospitals,
            '62' for all health care).

    Returns:
        List of matching records.

    Example::

        # Show all elections in NAICS 622 (hospitals)
        hospital_cases = filter_by_naics(result.cases, "622")
    """
    naics_prefix = naics_prefix.strip()
    if not naics_prefix:
        return []
    matches = []
    for record in records:
        code = _get_naics(record)
        if code and code.startswith(naics_prefix):
            matches.append(record)
    return matches


def filter_by_naics_sector(records, sector_code: str) -> list:
    """Filter records by 2-digit NAICS sector code."""
    return filter_by_naics(records, sector_code.strip()[:2])


def group_by_naics_sector(records) -> dict[str, list]:
    """Group records by their 2-digit NAICS sector code.

    Returns:
        Dict mapping sector codes to lists of records.
        Records without a NAICS code are grouped under ''.
    """
    groups: dict[str, list] = {}
    for record in records:
        code = _get_naics(record)
        sector = code[:2] if code else ""
        groups.setdefault(sector, []).append(record)
    return groups


def _get_naics(record) -> str:
    """Extract NAICS code from a record (dataclass, model, or dict)."""
    if isinstance(record, dict):
        return str(record.get("naics_code", "")).strip()
    return str(getattr(record, "naics_code", "")).strip()
