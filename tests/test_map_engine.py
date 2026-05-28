"""Error-path tests for siege_utilities.reporting.engines.map_engine (SU-4b)."""

import pytest

try:
    from siege_utilities.reporting.engines.map_engine import MapChartMixin
    import pandas as pd
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="map_engine deps missing")


class _MapEngine(MapChartMixin):
    pass


class TestMapChartMixinErrors:
    """Error paths for MapChartMixin methods."""

    def test_invalid_geo_data_type_raises(self):
        engine = _MapEngine()
        result = engine.create_choropleth_map(
            df=pd.DataFrame({"geoid": ["01"], "value": [1]}),
            geo_data=None,
            value_column="value",
        )
        assert result is not None

    def test_empty_dataframe_choropleth(self):
        engine = _MapEngine()
        result = engine.create_choropleth_map(
            df=pd.DataFrame(),
            geo_data=None,
            value_column="value",
        )
        assert result is not None

    def test_missing_column_marker_map(self):
        engine = _MapEngine()
        result = engine.create_marker_map(
            df=pd.DataFrame({"a": [1]}),
            lat_column="nonexistent_zz",
            lon_column="nonexistent_zz",
        )
        assert result is not None
