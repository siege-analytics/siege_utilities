"""
Engine mixins for the ChartGenerator class.

Each mixin defines a subset of chart-generation methods. At runtime they
are combined via multiple inheritance into the unified ``ChartGenerator``
class defined in ``chart_generator.py``.
"""

from .base_engine import BaseChartEngine
from .bar_engine import BarChartMixin
from .map_engine import MapChartMixin
from .stats_engine import StatsChartMixin
from .composite_engine import CompositeChartMixin

__all__ = [
    "BaseChartEngine",
    "BarChartMixin",
    "MapChartMixin",
    "StatsChartMixin",
    "CompositeChartMixin",
]
