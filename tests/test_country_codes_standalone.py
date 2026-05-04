"""Country-code lookups loaded via importlib, bypassing package __init__.

Companion to `test_country_codes.py`. The import-via-spec path catches
regressions where the geocoding module breaks under the package import
chain (e.g. an unrelated optional dep at `siege_utilities/__init__.py`
fails) but the module itself still works in isolation.
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GEOCODING_PATH = REPO_ROOT / "siege_utilities" / "geo" / "geocoding.py"

_spec = importlib.util.spec_from_file_location("_geocoding_isolated", GEOCODING_PATH)
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
