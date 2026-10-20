"""Error-path coverage (SU-4b) for siege_utilities.geo.crosswalk.crosswalk_client.

Forces the availability guards in CrosswalkClient.get_crosswalk for unsupported
years, unsupported geography, and missing crosswalk files. No network.
"""

import pytest

from siege_utilities.geo.crosswalk.crosswalk_client import (
    CrosswalkClient,
    CrosswalkUnavailable,
)


def test_get_crosswalk_rejects_unsupported_year_pair(tmp_path):
    client = CrosswalkClient(cache_dir=tmp_path)
    with pytest.raises(CrosswalkUnavailable) as exc_info:
        client.get_crosswalk(source_year=1999, target_year=2099, geography_level="tract")
    assert "not supported" in str(exc_info.value)
    assert isinstance(exc_info.value, ValueError)


def test_get_crosswalk_rejects_unsupported_geography_level(tmp_path):
    client = CrosswalkClient(cache_dir=tmp_path)
    # (2010, 2020) is a supported pair, but this geography level is not.
    with pytest.raises(CrosswalkUnavailable) as exc_info:
        client.get_crosswalk(source_year=2010, target_year=2020, geography_level="not_a_level")
    assert "not supported" in str(exc_info.value)


def test_get_crosswalk_reports_unconfigured_file(tmp_path):
    client = CrosswalkClient(cache_dir=tmp_path)
    with pytest.raises(CrosswalkUnavailable, match="No crosswalk file available.*2000->2010"):
        client.get_crosswalk(source_year=2000, target_year=2010, geography_level="tract")
