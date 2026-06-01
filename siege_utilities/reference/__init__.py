"""Reference data and crosswalks that ship with the library.

- :mod:`naics_soc_crosswalk` — NAICS / SOC code mapping and crosswalks
- :mod:`sample_data` — built-in demo datasets (synthetic + real Census mash-ups)

Submodules load on first attribute access via PEP 562 __getattr__.
"""

import importlib
import sys

_LAZY_IMPORTS: dict[str, str] = {}


def _register(names: list[str], module: str) -> None:
    for name in names:
        _LAZY_IMPORTS[name] = module


# --- naics_soc_crosswalk ---
_register([
    "NAICSCode",
    "NAICS_SECTORS",
    "parse_naics",
    "naics_ancestors",
    "naics_to_sector",
    "crosswalk_naics",
    "SOCCode",
    "SOC_MAJOR_GROUPS",
    "parse_soc",
    "soc_to_major_group",
    "fuzzy_match_naics",
    "NAICS_SUBSECTORS",
    "SOC_MINOR_GROUPS",
    "get_naics_lookup",
    "get_soc_lookup",
    "naics_title",
    "soc_title",
    "filter_by_naics",
    "filter_by_naics_sector",
    "group_by_naics_sector",
], ".naics_soc_crosswalk")

# --- sample_data ---
_register([
    "HOUSING_LOCALE_PRESETS",
    "SAMPLE_DATASETS",
    "CENSUS_SAMPLES",
    "SYNTHETIC_SAMPLES",
    "list_available_datasets",
    "get_dataset_info",
    "load_sample_data",
    "get_census_boundaries",
    "get_census_data",
    "join_boundaries_and_data",
    "create_sample_dataset",
    "get_census_county_sample",
    "get_metropolitan_sample",
    "generate_synthetic_population",
    "generate_synthetic_businesses",
    "generate_synthetic_housing",
], ".sample_data")

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        mod = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))
