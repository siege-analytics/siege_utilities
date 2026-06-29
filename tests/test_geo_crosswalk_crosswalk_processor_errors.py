"""Error-path coverage (SU-4b) for siege_utilities.geo.crosswalk.crosswalk_processor.

Forces the ValueError raised by CrosswalkProcessor.transform when the named
GEOID column is absent from the input DataFrame.
"""

import pandas as pd
import pytest

from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor


def _processor():
    crosswalk_df = pd.DataFrame(
        {"source_geoid": ["06001"], "target_geoid": ["06002"], "area_weight": [1.0]}
    )
    return CrosswalkProcessor(crosswalk_df, source_year=2010, target_year=2020, geography_level="tract")


def test_transform_raises_when_geoid_column_missing():
    proc = _processor()
    data = pd.DataFrame({"value": [1, 2, 3]})  # no GEOID column
    with pytest.raises(ValueError) as exc_info:
        proc.transform(data, geoid_column="GEOID")
    assert "GEOID column 'GEOID' not found" in str(exc_info.value)
