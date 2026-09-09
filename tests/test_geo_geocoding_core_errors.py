"""Error-path coverage (SU-4b) for siege_utilities.geo.geocoding_core."""

import pytest

from siege_utilities.geo.geocoding_core import get_country_code, get_country_name


def test_geocoding_core_country_name_raises_for_non_string_code():
    with pytest.raises(TypeError, match="country_code must be a string or None"):
        get_country_name(840)


def test_geocoding_core_country_code_raises_for_non_string_name():
    with pytest.raises(TypeError, match="country_name must be a string or None"):
        get_country_code(840)
