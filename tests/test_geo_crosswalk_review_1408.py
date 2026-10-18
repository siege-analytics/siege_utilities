"""Review regressions for the crosswalk error contract in issue #1408."""

import pandas as pd
import pytest

from siege_utilities.geo.crosswalk.crosswalk_processor import CrosswalkProcessor


def test_rate_merge_refusal_does_not_promise_automatic_fallback():
    xw = pd.DataFrame({"source_geoid": ["A", "B"], "target_geoid": ["T", "T"], "area_weight": [1.0, 1.0]})
    df = pd.DataFrame({"GEOID": ["A", "B"], "rate": [0.1, 0.9]})
    proc = CrosswalkProcessor(xw, 2010, 2020, "tract")
    with pytest.raises(ValueError) as exc:
        proc.transform(df, intensive_variables=["rate"])
    assert "falls back to tobler automatically" not in str(exc.value)


def test_crosswalk_unavailable_is_exported():
    import siege_utilities.geo.crosswalk as crosswalk_pkg
    from siege_utilities.geo.crosswalk import crosswalk_client
    assert "CrosswalkUnavailable" in crosswalk_client.__all__
    assert crosswalk_pkg.CrosswalkUnavailable is crosswalk_client.CrosswalkUnavailable
