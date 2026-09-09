"""Country-code lookups loaded via importlib, bypassing package __init__.

Companion to `test_country_codes.py`. The import-via-spec path catches
regressions where stdlib-only geocoding helpers accidentally become tied
to the package import chain or optional geocoding dependencies.
"""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GEOCODING_CORE_PATH = REPO_ROOT / "siege_utilities" / "geo" / "geocoding_core.py"

_spec = importlib.util.spec_from_file_location(
    "siege_utilities.geo.geocoding_core", GEOCODING_CORE_PATH
)
geocoding = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(geocoding)


CODE_TO_NAME = {
    "us": "United States",
    "ca": "Canada",
    "gb": "United Kingdom",
    "de": "Germany",
    "fr": "France",
    "jp": "Japan",
    "au": "Australia",
}


def test_get_country_name_known_codes():
    for code, expected in CODE_TO_NAME.items():
        assert geocoding.get_country_name(code) == expected


def test_get_country_code_known_names():
    for name, expected in {v: k for k, v in CODE_TO_NAME.items()}.items():
        assert geocoding.get_country_code(name) == expected


def test_round_trip():
    for code in CODE_TO_NAME:
        assert geocoding.get_country_code(geocoding.get_country_name(code)) == code


def test_list_countries_returns_nonempty_dict_with_known_codes():
    countries = geocoding.list_countries()
    assert isinstance(countries, dict)
    assert len(countries) >= len(CODE_TO_NAME)
    for code in CODE_TO_NAME:
        assert code in countries


def test_get_country_name_is_case_insensitive():
    assert geocoding.get_country_name("US") == "United States"
    assert geocoding.get_country_name("Us") == "United States"


def test_get_country_code_is_case_insensitive():
    assert geocoding.get_country_code("united states") == "us"
    assert geocoding.get_country_code("UNITED STATES") == "us"


def test_unknown_inputs_have_documented_fallbacks():
    assert geocoding.get_country_name("zz") == "zz"
    assert geocoding.get_country_name("") == ""
    assert geocoding.get_country_code("Atlantis") is None
    assert geocoding.get_country_code("") is None


def test_standalone_country_helpers_handle_missing_data_and_reject_non_strings():
    assert geocoding.get_country_name(None) is None
    assert geocoding.get_country_code(None) is None
    with pytest.raises(TypeError):
        geocoding.get_country_name(840)
    with pytest.raises(TypeError):
        geocoding.get_country_code(840)


def test_standalone_concatenate_addresses_coerces_realistic_components():
    assert geocoding.concatenate_addresses(
        street=" 123 Main St ",
        city="Austin",
        state_province_area="TX",
        postal_code=78701,
        country="US",
    ) == "123 Main St, Austin, TX, 78701, US"
    assert geocoding.concatenate_addresses(postal_code=0) == "0"
    assert geocoding.concatenate_addresses(street="", city="   ", postal_code=None) == ""
