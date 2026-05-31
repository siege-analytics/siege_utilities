"""Property tests for census_constants — SU-1 invariants.

Tests that normalization functions are idempotent and that
invalid inputs produce clear errors, not silent garbage.
"""

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, example, settings
import hypothesis.strategies as st


VALID_STATE_FIPS = [
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12",
    "13", "15", "16", "17", "18", "19", "20", "21", "22", "23",
    "24", "25", "26", "27", "28", "29", "30", "31", "32", "33",
    "34", "35", "36", "37", "38", "39", "40", "41", "42", "44",
    "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56",
]


class TestNormalizeStateIdentifierProperties:
    """Property tests for normalize_state_identifier."""

    @given(st.sampled_from(VALID_STATE_FIPS))
    def test_idempotent_on_valid_fips(self, fips):
        """Normalizing a valid FIPS code twice returns the same result."""
        from siege_utilities.config.census_constants import normalize_state_identifier

        result = normalize_state_identifier(fips)
        assert normalize_state_identifier(result) == result

    @given(st.text(max_size=50))
    @settings(max_examples=100)
    def test_never_returns_invalid_fips(self, raw):
        """If normalization succeeds, the result must be a 2-digit string."""
        from siege_utilities.config.census_constants import normalize_state_identifier

        try:
            result = normalize_state_identifier(raw)
            assert isinstance(result, str)
            assert len(result) == 2
            assert result.isdigit()
        except (ValueError, KeyError):
            pass

    @given(st.integers(min_value=100, max_value=99999))
    def test_rejects_out_of_range_numbers(self, n):
        """Numbers outside valid FIPS range should raise, not return garbage."""
        from siege_utilities.config.census_constants import normalize_state_identifier

        try:
            result = normalize_state_identifier(str(n))
            assert result in VALID_STATE_FIPS, f"Unexpected FIPS: {result} from {n}"
        except (ValueError, KeyError):
            pass

    @example("")
    @example("ZZ")
    @example("00")
    @example("99")
    @given(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=3, max_size=20))
    def test_invalid_alpha_rejects_or_resolves(self, name):
        """Arbitrary alpha strings either resolve to valid FIPS or raise."""
        from siege_utilities.config.census_constants import normalize_state_identifier

        try:
            result = normalize_state_identifier(name)
            assert result in VALID_STATE_FIPS
        except (ValueError, KeyError):
            pass
