"""
Name-normalization functions for use as stable seeds to UUID5 generators.

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
}


_PUNCTUATION_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


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
