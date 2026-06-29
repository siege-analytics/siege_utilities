"""Error-path coverage (SU-4b) for siege_utilities.geo.crosswalk.crosswalk_client.

Forces the ValueError guards in CrosswalkClient.get_crosswalk for an
unsupported year combination and an unsupported geography level. No network.
"""

import pytest

from siege_utilities.geo.crosswalk.crosswalk_client import CrosswalkClient


def test_get_crosswalk_rejects_unsupported_year_pair(tmp_path):
    client = CrosswalkClient(cache_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        client.get_crosswalk(source_year=1999, target_year=2099, geography_level="tract")
    assert "not supported" in str(exc_info.value)


def test_get_crosswalk_rejects_unsupported_geography_level(tmp_path):
    client = CrosswalkClient(cache_dir=tmp_path)
    # (2010, 2020) is a supported pair, but this geography level is not.
    with pytest.raises(ValueError) as exc_info:
        client.get_crosswalk(source_year=2010, target_year=2020, geography_level="not_a_level")
    assert "not supported" in str(exc_info.value)
