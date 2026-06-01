"""Statistical primitives for DataFrame analysis.

- :mod:`cross_tabulation` — contingency tables, chi-square, proportion math
- :mod:`moe_propagation` — ACS margin-of-error propagation through derived estimates

Submodules load on first attribute access via PEP 562 __getattr__.
"""

import importlib
import sys

_LAZY_IMPORTS: dict[str, str] = {}


def _register(names: list[str], module: str) -> None:
    for name in names:
        _LAZY_IMPORTS[name] = module


# --- cross_tabulation ---
_register([
    "ChiSquareResult",
    "CrossTabSpec",
    "chi_square_test",
    "contingency_table",
    "moe_cross_tab",
    "rate_table",
], ".cross_tabulation")

# --- moe_propagation ---
_register([
    "Estimate",
    "Z_90",
    "flag_unreliable",
    "moe_difference",
    "moe_product",
    "moe_proportion",
    "moe_ratio",
    "moe_sum",
], ".moe_propagation")

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
