"""Country-code lookups via the package import path.

Pairs with `test_country_codes_standalone.py`, which exercises the same
functions but loads the geocoding module directly via importlib. Both
should agree on the round-trip.
"""

from siege_utilities.geo.geocoding import (
    get_country_name,
    get_country_code,
    list_countries,
)

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
        assert get_country_name(code) == expected


def test_get_country_code_known_names():
    for name, expected in {v: k for k, v in CODE_TO_NAME.items()}.items():
        assert get_country_code(name) == expected


def test_round_trip():
    for code in CODE_TO_NAME:
        assert get_country_code(get_country_name(code)) == code


def test_list_countries_returns_nonempty_dict_with_known_codes():
    countries = list_countries()
    assert isinstance(countries, dict)
    assert len(countries) >= len(CODE_TO_NAME)
    for code in CODE_TO_NAME:
        assert code in countries
