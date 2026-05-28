"""Error-path tests for siege_utilities.geo.crosswalk.crosswalk_client (SU-4b)."""

import pytest

try:
    from siege_utilities.geo.crosswalk.crosswalk_client import CrosswalkClient
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="pandas or crosswalk deps missing")


class TestCrosswalkClientErrors:
    """Error paths for CrosswalkClient.get_crosswalk."""

    def test_unsupported_year_pair_raises(self, tmp_path):
        """Unsupported year pair must raise ValueError."""
        client = CrosswalkClient(cache_dir=tmp_path)
        with pytest.raises(ValueError, match="not supported"):
            client.get_crosswalk(source_year=1900, target_year=1950)

    def test_unsupported_geography_raises(self, tmp_path):
        """Unsupported geography level must raise ValueError."""
        client = CrosswalkClient(cache_dir=tmp_path)
        with pytest.raises(ValueError, match="not supported"):
            client.get_crosswalk(
                source_year=2010, target_year=2020, geography_level="galaxy"
            )
