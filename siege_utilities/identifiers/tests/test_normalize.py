"""
Name normalization tests. Changes here signal a v1 correctness violation —
every UUID seeded with normalize_name_v1 would drift.
"""

from siege_utilities.identifiers.normalize import (
    NORMALIZER_VERSIONS,
    normalize_name_v1,
)


def test_empty_input_returns_empty():
    assert normalize_name_v1("") == ""
    assert normalize_name_v1(None) == ""  # type: ignore[arg-type]


def test_casefold_lowercases():
    assert normalize_name_v1("JOHN SMITH") == "john smith"


def test_strips_diacritics():
    assert normalize_name_v1("José García") == "jose garcia"
    assert normalize_name_v1("Beyoncé") == "beyonce"
    assert normalize_name_v1("Jürgen Müller") == "jurgen muller"


def test_strips_punctuation():
    assert normalize_name_v1("O'Brien, Jr.") == "obrien jr"
    assert normalize_name_v1("Smith-Jones") == "smithjones"


def test_collapses_multi_whitespace():
    assert normalize_name_v1("John    Smith") == "john smith"
    assert normalize_name_v1("John\tSmith\nDoe") == "john smith doe"


def test_strips_leading_trailing_whitespace():
    assert normalize_name_v1("  John Smith  ") == "john smith"


def test_preserves_internal_word_boundaries():
    assert normalize_name_v1("Van Der Berg") == "van der berg"


def test_nfkd_compatibility_decomposition():
    assert normalize_name_v1("ﬁre") == "fire"


def test_v1_is_stable_for_known_inputs():
    """Frozen v1 behavior. Any change signals a correctness violation."""
    known = [
        ("John Smith", "john smith"),
        ("Ángel Peña", "angel pena"),
        ("O'Reilly & Sons, LLC", "oreilly sons llc"),
        ("  MARY-ELLEN   ", "maryellen"),
    ]
    for raw, expected in known:
        assert normalize_name_v1(raw) == expected, f"v1 changed output for {raw!r}"


def test_normalizer_versions_registry_includes_v1():
    assert "normalize_name_v1" in NORMALIZER_VERSIONS
    assert NORMALIZER_VERSIONS["normalize_name_v1"]  # non-empty description
