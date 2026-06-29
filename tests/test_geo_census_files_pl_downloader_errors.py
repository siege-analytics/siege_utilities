"""Error-path coverage (SU-4b) for siege_utilities.geo.census_files.pl_downloader.

Forces the ValueError guards on unsupported years (_build_geo_url) and
unknown geography levels (get_data), with no network access.
"""

import pytest

from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader


def test_build_geo_url_rejects_unsupported_year(tmp_path):
    dl = PLFileDownloader(cache_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        dl._build_geo_url("ca", 1999)
    assert "only available for 2010 and 2020" in str(exc_info.value)


def test_get_data_rejects_unknown_geography(tmp_path):
    dl = PLFileDownloader(cache_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        dl.get_data("CA", year=2020, geography="not_a_level")
    assert "Unknown geography level" in str(exc_info.value)
