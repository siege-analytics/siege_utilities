"""
Reference data and crosswalks that ship with the library.

- :mod:`naics_soc_crosswalk` — NAICS / SOC code mapping and crosswalks
- :mod:`sample_data` — built-in demo datasets (synthetic + real Census mash-ups)

Extracted from ``data/`` during ELE-2437. Reference data (static tables,
crosswalks, fixtures) is a distinct nature from DataFrame ops
(``siege_utilities.data.statistics``) and infrastructure
(``siege_utilities.engines``).
"""

from .naics_soc_crosswalk import *  # noqa: F401, F403
from .sample_data import *  # noqa: F401, F403
