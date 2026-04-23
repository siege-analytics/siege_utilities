"""
Integration test for CensusAPIClient Django cache backend.

Verifies the set/get round-trip through Django's cache framework
using LocMemCache (configured in tests/django_project/settings.py).
"""

import pytest
import pandas as pd

# Skip if Django/GDAL not available
try:
    from django.core.cache import cache

    _DJANGO_AVAILABLE = True
except Exception:
    _DJANGO_AVAILABLE = False


@pytest.mark.skipif(not _DJANGO_AVAILABLE, reason="Django not available")
class TestCensusAPIDjangoCacheRoundTrip:
    """Test CensusAPIClient with cache_backend='django'."""

    def setup_method(self):
        if _DJANGO_AVAILABLE:
            cache.clear()

    def test_client_accepts_django_backend(self):
        from siege_utilities.geo.census_api_client import CensusAPIClient

        client = CensusAPIClient(cache_backend="django")
        assert client.cache_backend == "django"

    def test_django_cache_set_get_roundtrip(self):
        """Verify data survives a set→get cycle through Django cache."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        client = CensusAPIClient(cache_backend="django")

        df = pd.DataFrame(
            {
                "GEOID": ["06037", "06059", "06071"],
                "B01001_001E": [10000000, 3200000, 2200000],
            }
        )

        cache_key = "test_roundtrip_key"
        client._django_cache_set(cache_key, df)

        result = client._django_cache_get(cache_key)
        assert result is not None
        assert list(result.columns) == list(df.columns)
        assert len(result) == len(df)
        assert result["GEOID"].tolist() == df["GEOID"].tolist()
        assert result["B01001_001E"].tolist() == df["B01001_001E"].tolist()

    def test_django_cache_miss_returns_none(self):
        from siege_utilities.geo.census_api_client import CensusAPIClient

        client = CensusAPIClient(cache_backend="django")
        result = client._django_cache_get("nonexistent_key")
        assert result is None

    def test_django_cache_overwrite(self):
        """Verify that re-setting a key overwrites the old value."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        client = CensusAPIClient(cache_backend="django")
        cache_key = "overwrite_test"

        df1 = pd.DataFrame({"A": [1, 2, 3]})
        df2 = pd.DataFrame({"A": [4, 5, 6]})

        client._django_cache_set(cache_key, df1)
        client._django_cache_set(cache_key, df2)

        result = client._django_cache_get(cache_key)
        assert result is not None
        assert result["A"].tolist() == [4, 5, 6]

    def test_django_cache_preserves_dtypes(self):
        """Verify numeric and string columns survive the round-trip."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        client = CensusAPIClient(cache_backend="django")
        cache_key = "dtype_test"

        df = pd.DataFrame(
            {
                "geoid": ["01001", "02002"],
                "population": [55000, 32000],
                "median_income": [45123.50, 62890.25],
            }
        )
        client._django_cache_set(cache_key, df)
        result = client._django_cache_get(cache_key)

        assert result is not None
        assert result["geoid"].tolist() == ["01001", "02002"]
        assert result["population"].tolist() == [55000, 32000]
        assert abs(result["median_income"].iloc[0] - 45123.50) < 0.01

    def test_django_cache_empty_dataframe(self):
        """Verify empty DataFrames round-trip correctly."""
        from siege_utilities.geo.census_api_client import CensusAPIClient

        client = CensusAPIClient(cache_backend="django")
        cache_key = "empty_df_test"

        df = pd.DataFrame({"A": [], "B": []})
        client._django_cache_set(cache_key, df)
        result = client._django_cache_get(cache_key)

        assert result is not None
        assert len(result) == 0
