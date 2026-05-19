"""
Engine abstractions — engine-agnostic DataFrame operations.

Holds the :class:`DataFrameEngine` ABC and its four concrete
implementations (Pandas, DuckDB, Spark, PostGIS).

Promoted from ``data/`` during ELE-2437 because the engine layer is
infrastructure ("how we compute"), distinct from ``data/statistics/``
(stats primitives) and ``reference/`` (reference / sample data).
"""

from .dataframe_engine import *  # noqa: F401, F403

try:
    from .dataframe_engine import __all__  # noqa: F401
except ImportError:
    pass
