"""
Name, phone and address normalization functions for use as stable seeds to
UUID5 generators.

Each version is pinned forever — consumers record which version was used
to seed a given entity, and any change that would alter output for any
input is a correctness violation (would drift UUIDs).

New normalization behavior goes in a new version (normalize_name_v2...),
never as a modification to an existing version. The consumer's
``entity_identifiers`` table (or equivalent) should carry a
``canonical_seed_version`` column so the pinning is explicit.
"""

import re
import unicodedata

NORMALIZER_VERSIONS: dict[str, str] = {
    "normalize_name_v1": (
        "Initial version. Unicode NFKD decomposition with combining-mark "
        "removal, locale-independent casefold, strip non-word punctuation "
        "while preserving word characters and whitespace, collapse "
        "multi-whitespace to single space, strip leading/trailing whitespace."
    ),
    "normalize_phone_v1": (
        "Initial version. Drop a trailing extension (x, ext, extension), keep "
        "ASCII digits only, drop a leading US country code 1 when the result "
        "has 11 digits; fewer than 7 digits is empty."
    ),
    "normalize_address_v1": (
        "Initial version. Components normalized separately: NFKD with "
        "combining marks removed, casefold, punctuation to spaces, collapse "
        "whitespace. Street: USPS street-suffix and directional "
        "abbreviations, unit designators (#, apt, unit, suite, ...) unified "
        "to 'unit'. State: US state and territory names to postal codes. "
        "Postal code: first five digits, zero-padded. Joined with ' | '."
    ),
}


_PUNCTUATION_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")
_NON_DIGIT_RE = re.compile(r"[^0-9]")
_PHONE_EXTENSION_RE = re.compile(r"\s*(?:extension|ext\.?|x)\s*\d+\s*$", flags=re.IGNORECASE)
_ADDRESS_PUNCTUATION_RE = re.compile(r"[^\w\s]|_", flags=re.UNICODE)

# USPS Publication 28 standard abbreviations (common subset) for the street
# line. Frozen for v1.
_STREET_ABBREVIATIONS: dict[str, str] = {
    # Street suffixes
    "alley": "aly", "avenue": "ave", "av": "ave", "boulevard": "blvd",
    "circle": "cir", "court": "ct", "drive": "dr", "expressway": "expy",
    "freeway": "fwy", "highway": "hwy", "lane": "ln", "parkway": "pkwy",
    "place": "pl", "plaza": "plz", "road": "rd", "square": "sq",
    "street": "st", "terrace": "ter", "trail": "trl", "turnpike": "tpke",
    # Directionals
    "north": "n", "south": "s", "east": "e", "west": "w",
    "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
    # Unit designators, unified so "#2", "Apt 2" and "Suite 2" compare equal
    "apartment": "unit", "apt": "unit", "suite": "unit", "ste": "unit",
    "unit": "unit", "room": "unit", "rm": "unit", "no": "unit",
}
# US state, DC and territory names to USPS postal codes, for the state field
# only. Frozen for v1.
_STATE_CODES: dict[str, str] = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar",
    "california": "ca", "colorado": "co", "connecticut": "ct",
    "delaware": "de", "florida": "fl", "georgia": "ga", "hawaii": "hi",
    "idaho": "id", "illinois": "il", "indiana": "in", "iowa": "ia",
    "kansas": "ks", "kentucky": "ky", "louisiana": "la", "maine": "me",
    "maryland": "md", "massachusetts": "ma", "michigan": "mi",
    "minnesota": "mn", "mississippi": "ms", "missouri": "mo",
    "montana": "mt", "nebraska": "ne", "nevada": "nv", "ohio": "oh",
    "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa", "tennessee": "tn",
    "texas": "tx", "utah": "ut", "vermont": "vt", "virginia": "va",
    "washington": "wa", "wisconsin": "wi", "wyoming": "wy",
    "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm",
    "new york": "ny", "north carolina": "nc", "north dakota": "nd",
    "rhode island": "ri", "south carolina": "sc", "south dakota": "sd",
    "west virginia": "wv", "district of columbia": "dc", "puerto rico": "pr",
}

__all__ = [
    "normalize_address_v1",
    "normalize_name_v1",
    "normalize_phone_v1",
]


def normalize_name_v1(name: str) -> str:
    """
    Normalize a human-readable name to a stable seed string.

    Rules (v1, frozen):
    - NFKD decomposition, drop Unicode combining marks (strips accents)
    - Casefold (lowercase; locale-independent)
    - Strip punctuation except word characters and whitespace
    - Collapse multi-whitespace to single space
    - Strip leading/trailing whitespace

    Returns an empty string if input is ``None`` or empty after
    normalization. Consumers that need a fallback seed ladder should
    detect empty output and fall through to a different identifier.

    This function MUST NOT be modified. New normalization behavior goes
    in a new version function.
    """
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    no_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    cased = no_marks.casefold()
    no_punct = _PUNCTUATION_RE.sub("", cased)
    collapsed = _WHITESPACE_RE.sub(" ", no_punct)
    return collapsed.strip()


def normalize_phone_v1(phone: str) -> str:
    """
    Normalize a phone number to a stable comparison key.

    Rules (v1, frozen):
    - Drop a trailing extension (``x12``, ``ext. 12``, ``extension 12``)
    - Keep ASCII digits only
    - Drop a leading US country code ``1`` when 11 digits remain
    - Return an empty string when fewer than 7 digits remain, so fragments
      are never treated as identity evidence

    ``"(512) 555-0100"``, ``"512-555-0100"``, ``"+1 512 555 0100"`` and
    ``"512-555-0100 x12"`` all become ``"5125550100"``. Numbers with another
    country code keep it.

    This function MUST NOT be modified. New behavior goes in a new version.
    """
    if not phone:
        return ""
    without_extension = _PHONE_EXTENSION_RE.sub("", str(phone))
    digits = _NON_DIGIT_RE.sub("", without_extension)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) >= 7 else ""


def _fold_address_text(value: str) -> list[str]:
    decomposed = unicodedata.normalize("NFKD", str(value).replace("#", " unit "))
    no_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    spaced = _ADDRESS_PUNCTUATION_RE.sub(" ", no_marks.casefold())
    return _WHITESPACE_RE.sub(" ", spaced).strip().split()


def normalize_address_v1(
    street: str, city: str = "", state: str = "", postal_code: str = "",
) -> str:
    """
    Normalize postal address components to a stable comparison key.

    Rules (v1, frozen). Each component is NFKD-decomposed with combining
    marks removed, casefolded, punctuation replaced with spaces and
    whitespace collapsed, then:

    - street: USPS Publication 28 street-suffix and directional
      abbreviations (``avenue`` -> ``ave``, ``north`` -> ``n``); unit
      designators (``#``, ``apt``, ``apartment``, ``suite``, ``ste``,
      ``unit``, ``room``, ``no``) all become ``unit``
    - city: folded only
    - state: a US state, DC or territory name becomes its postal code
      (``Texas`` -> ``tx``, ``New York`` -> ``ny``); other values are folded
    - postal_code: the first five digits, left-padded with zeros so a ZIP
      stored as a number (``2134``) matches ``02134``; ZIP+4 keeps the ZIP

    Components are joined with ``" | "`` so a word cannot move between
    fields. Returns an empty string when the street is empty: city, state or
    ZIP alone is not an address. This is a comparison key, not a deliverable
    USPS address; it does not validate that the address exists.

    This function MUST NOT be modified. New behavior goes in a new version.
    """
    street_tokens = [_STREET_ABBREVIATIONS.get(token, token) for token in _fold_address_text(street or "")]
    if not street_tokens:
        return ""
    state_text = " ".join(_fold_address_text(state or ""))
    zip_digits = _NON_DIGIT_RE.sub("", str(postal_code or ""))[:5]
    parts = [
        " ".join(street_tokens),
        " ".join(_fold_address_text(city or "")),
        _STATE_CODES.get(state_text, state_text),
        zip_digits.zfill(5) if zip_digits else "",
    ]
    return " | ".join(parts)
