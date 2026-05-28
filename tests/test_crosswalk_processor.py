"""Error-path tests for siege_utilities.geo.crosswalk.crosswalk_processor (SU-4b)."""

import pytest

try:
    import pandas as pd
    from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="pandas or crosswalk deps missing")


class TestCrosswalkProcessorErrors:
    """Error paths for CrosswalkProcessor.transform."""

    def test_missing_geoid_column_raises(self):
        """DataFrame without GEOID column must raise ValueError."""
        crosswalk_df = pd.DataFrame({
            "source_geoid": ["01001"],
            "target_geoid": ["01002"],
            "area_weight": [1.0],
        })
        proc = CrosswalkProcessor(
            crosswalk_df=crosswalk_df,
            source_year=2010,
            target_year=2020,
            geography_level="tract",
        )
        df = pd.DataFrame({"value": [100]})
        with pytest.raises(ValueError, match="GEOID column"):
            proc.transform(df)
