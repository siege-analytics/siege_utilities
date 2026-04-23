"""
siege_utilities.survey — Survey/crosstab report engine.

Modelled on the Quantipy Stack → Cluster → Chain → View hierarchy,
built fresh for Python 3.12 on pandas + weightipy.

Install the optional dependency:
    pip install siege-utilities[survey]

Quick start::

    from siege_utilities.survey import build_chain, chain_to_argument
    from siege_utilities.reporting.pages.page_models import TableType

    chain = build_chain(df, row_var="party", break_vars=["county"],
                        table_type=TableType.SINGLE_RESPONSE, geo_column="county")
    argument = chain_to_argument(chain, headline="Party ID by County",
                                 narrative="Democrats lead in metro counties.")
"""

import importlib
import sys

_LAZY = {
    "Stack":           ".models",
    "Cluster":         ".models",
    "Chain":           ".models",
    "View":            ".models",
    "WeightScheme":    ".models",
    "WeightingConvergenceError": ".weights",
    "apply_rim_weights": ".weights",
    "build_chain":     ".crosstab",
    "column_proportion_test": ".significance",
    "chi_square_flag": ".significance",
    "chain_to_argument":   ".render",
    "stack_to_arguments":  ".render",
}

__all__ = list(_LAZY.keys())


def __getattr__(name):
    if name in _LAZY:
        mod = importlib.import_module(_LAZY[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY.keys())))
