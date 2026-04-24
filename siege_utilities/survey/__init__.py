"""
siege_utilities.survey — Survey/crosstab report engine.

Modelled on the Quantipy Stack → Cluster → Chain → View hierarchy,
built fresh for Python 3.12 on pandas + weightipy.

Install the optional dependency:
    pip install siege-utilities[survey]

**Hierarchy**

* ``View``  — one cell statistic (count, pct, CI)
* ``Chain`` — one crosstab (row_var × break_vars)
* ``Cluster`` — a named group of Chains = one report section
* ``Stack`` — a complete report (all Clusters + shared WeightScheme)

**Waves (longitudinal surveys)**

* ``Wave``    — the same questionnaire fielded at a single point in time
                (carries ``df`` and optionally a per-wave ``Stack``)
* ``WaveSet`` — an ordered set of Waves; ``compare_chain`` produces a
                LONGITUDINAL Chain aligned across waves

A Stack describes **one** fielding. A WaveSet composes **many** fieldings
into change detection / trend output. Use a Stack when you have a single
snapshot; use a WaveSet to track the same question across time.

Quick start::

    from siege_utilities.survey import build_chain, chain_to_argument
    from siege_utilities.reporting.pages.page_models import TableType

    chain = build_chain(df, row_var="party", break_vars=["county"],
                        table_type=TableType.SINGLE_RESPONSE, geo_column="county")
    argument = chain_to_argument(chain, headline="Party ID by County",
                                 narrative="Democrats lead in metro counties.")

Longitudinal (multi-wave) example::

    from datetime import date
    from siege_utilities.survey import Wave, WaveSet

    waveset = WaveSet(name="2024 tracker", waves=[
        Wave(id="W1", date=date(2024, 3, 1), df=df_march),
        Wave(id="W2", date=date(2024, 6, 1), df=df_june),
        Wave(id="W3", date=date(2024, 9, 1), df=df_sept),
    ])
    chain = waveset.compare_chain(row_var="party")
    # chain.views keyed by wave id; delta column appended automatically.
"""

import importlib
import sys

_LAZY = {
    "Stack":           ".models",
    "Cluster":         ".models",
    "Chain":           ".models",
    "View":            ".models",
    "Wave":            ".models",
    "WaveSet":         ".models",
    "WeightScheme":    ".models",
    "WeightingConvergenceError": ".weights",
    "apply_rim_weights": ".weights",
    "build_chain":     ".crosstab",
    "column_proportion_test": ".significance",
    "chi_square_flag": ".significance",
    "chain_to_argument":   ".render",
    "stack_to_arguments":  ".render",
    "compare_waves":   ".waves",
    "WavesError":      ".waves",
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
