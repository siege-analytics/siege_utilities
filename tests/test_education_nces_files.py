"""Tests for siege_utilities.education.nces.files (SU#534)."""

import pytest

from siege_utilities.education.nces import NCESFiles


class TestParseSchoolYear:

    def test_basic(self):
        assert NCESFiles._parse_school_year("2022-23") == (2022, 2023)

    def test_decade_rollover(self):
        assert NCESFiles._parse_school_year("2009-10") == (2009, 2010)

    def test_century_rollover(self):
        # The fix from socialwarehouse PR #218 — suffix is decorative;
        # end = start + 1 always.
        assert NCESFiles._parse_school_year("2099-00") == (2099, 2100)

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            NCESFiles._parse_school_year("2022")


def test_import_paths():
    """Documented import paths resolve to the same class."""
    from siege_utilities.education.nces import NCESFiles as n1
    from siege_utilities.education.nces.files import NCESFiles as n2

    assert n1 is n2
