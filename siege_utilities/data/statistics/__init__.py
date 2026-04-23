"""
Statistical primitives for DataFrame analysis.

- :mod:`cross_tabulation` — contingency tables, chi-square, proportion math
- :mod:`moe_propagation` — ACS margin-of-error propagation through derived estimates

Extracted from top-level ``data/`` during ELE-2437 so tabulation / stats
primitives live together, distinct from engine infrastructure
(``siege_utilities.engines``) and reference data (``siege_utilities.reference``).
"""

from .cross_tabulation import *  # noqa: F401, F403
from .moe_propagation import *  # noqa: F401, F403
