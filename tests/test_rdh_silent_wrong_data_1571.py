"""Reviewer pre-check for #1571. No network: session mocked, dummy files under tmp_path."""
import io
import logging
import warnings
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.geo.providers import redistricting_data_hub as rdh
from siege_utilities.geo.providers.redistricting_data_hub import (
    RDH_MAX_RESULTS, RDHClient, RDHDataset, fetch_cvap, fetch_pl94171,
)


@pytest.fixture
def client(tmp_path):
    c = RDHClient(username="dummy-user", password="dummy-pass", cache_dir=tmp_path / "cache")
    c._session = MagicMock()
    yield c


def _picked(client):
    client.load_csv = lambda ds, **kw: ds  # report which dataset would be loaded
    return client


# 1. geography filter
def test_block_does_not_match_block_group(client):
    _picked(client).get_pl94171_data = lambda s, year=None: [
        RDHDataset("VA PL 94-171 2020 Block Group", "https://x/a.csv"),
        RDHDataset("VA PL 94-171 2020 Block", "https://x/b.csv")]
    assert fetch_pl94171("VA", geography="block", client=client).title.endswith(" Block")


def test_block_group_spelling_matches_block_group_title(client):
    _picked(client).get_cvap_data = lambda s, year=None: [
        RDHDataset("VA CVAP 2020 County", "https://x/c.csv"),
        RDHDataset("VA CVAP 2020 Block Group", "https://x/bg.csv")]
    assert fetch_cvap("VA", geography="block_group", client=client).title.endswith("Block Group")


def test_unmatched_geography_raises_instead_of_falling_back(client):
    _picked(client).get_cvap_data = lambda s, year=None: [RDHDataset("VA CVAP 2020 County", "https://x/c.csv")]
    with pytest.raises(FileNotFoundError, match="County"):  # names what is available
        fetch_cvap("VA", geography="tract", client=client)


# 2. GEOID leading zeros
def test_load_csv_keeps_geoid_like_columns_as_strings(client, tmp_path):
    csv = tmp_path / "al_cvap.csv"
    csv.write_text("GEOID20,STATEFP,COUNTYFP,CVAP_TOT\n01001020100,01,001,1234\n")
    df = client.load_csv(csv)
    assert df.loc[0, ["GEOID20", "STATEFP", "COUNTYFP"]].tolist() == ["01001020100", "01", "001"]


# 3. cache hit returns the same kind of path
def test_cached_zip_returns_extracted_directory_like_first_download(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("va_cvap.csv", "GEOID,CVAP\n51001,1\n")
    resp = MagicMock()
    resp.iter_content.return_value = [buf.getvalue()]
    client._session.get.return_value = resp
    ds = RDHDataset("VA CVAP 2020 County", "https://redistrictingdatahub.org/x/va_cvap.zip")
    first = client.download_dataset(ds)
    second = client.download_dataset(ds)
    assert first.is_dir() and second.is_dir() and first == second


# 4. ambiguous archive member
def test_ambiguous_csv_member_raises(client, tmp_path):
    d = tmp_path / "extracted"
    d.mkdir()
    (d / "b_county.csv").write_text("GEOID\n01001\n")
    (d / "a_tract.csv").write_text("GEOID\n01001020100\n")
    with pytest.raises((ValueError, FileNotFoundError)):
        client.load_csv(d)


# 5. listing at the API cap
def test_listing_at_max_results_is_paged_or_warned(client, caplog):
    entries = [{"title": f"VA dataset {i}", "url": f"https://x/{i}.csv"} for i in range(RDH_MAX_RESULTS)]
    resp = MagicMock()
    resp.json.side_effect = [entries, []]
    client._session.get.return_value = resp
    with patch.object(rdh, "log_warning") as log_warning, warnings.catch_warnings(record=True) as w, \
            caplog.at_level(logging.WARNING):
        warnings.simplefilter("always")
        client.list_datasets(states=["VA"])
    paged = client._session.get.call_count > 1
    warned = log_warning.called or bool(w) or any(r.levelno >= logging.WARNING for r in caplog.records)
    assert paged or warned
