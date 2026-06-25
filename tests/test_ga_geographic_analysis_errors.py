"""Error-path coverage (SU-4b) for reporting.examples.ga_geographic_analysis."""
import pandas as pd
import pytest
from siege_utilities.reporting.examples.ga_geographic_analysis import aggregate_by_state


def test_aggregate_by_state_raises_when_no_valid_state_fips():
    df = pd.DataFrame({"state": ["X"], "state_fips": [None], "sessions": [1], "users": [1]})
    with pytest.raises(ValueError) as exc_info:
        aggregate_by_state(df)
    assert "valid state_fips" in str(exc_info.value)
