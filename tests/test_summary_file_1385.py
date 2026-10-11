"""Offline ACS Summary File contracts using observed Census table slices."""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, call

import pandas as pd
import pytest
import requests
from pandas.testing import assert_frame_equal
from requests.exceptions import ConnectionError, HTTPError, Timeout

from siege_utilities.geo.census.api import CensusAPI
from siege_utilities.geo.census.dual_source import (
    AlternationPolicy,
    ApiSource,
    BulkFileSource,
    DualSourceCensusClient,
    Provenance,
    api_to_summary_variable,
    summary_to_api_variable,
)
from siege_utilities.geo.census.variable_registry import VariableRegistry
from siege_utilities.geo.census_api_client import CensusAPIError, CensusRateLimitError


FIXTURES = Path(__file__).parent / "data" / "summary_file"
BASE = "https://www2.census.gov/programs-surveys/acs/summary_file"
POPULATION_URL = f"{BASE}/2022/table-based-SF/data/1YRData/acsdt1y2022-b01003.dat"
INCOME_URL = f"{BASE}/2022/table-based-SF/data/1YRData/acsdt1y2022-b19013.dat"
REQUEST = dict(
    variables=["B01003_001E"], year=2022, dataset="acs1",
    geography="county", state_fips="06", include_moe=False,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(
        "requests.sessions.Session.request",
        Mock(side_effect=AssertionError("Live network is forbidden")),
    )


def response_for(body: bytes, url: str = POPULATION_URL, status: int = 200):
    response = requests.Response()
    response.status_code = status
    response.url = url
    response.raw = BytesIO(body)
    return response


@pytest.fixture
def download(monkeypatch):
    def get(url, **kwargs):
        return response_for((FIXTURES / url.rsplit("/", 1)[1]).read_bytes(), url)

    mocked = Mock(side_effect=get)
    monkeypatch.setattr("requests.get", mocked)
    return mocked


@pytest.fixture
def source(tmp_path):
    # Small chunks exercise filtering/concatenation across chunk boundaries.
    return BulkFileSource(cache_dir=tmp_path / "cache", chunksize=2)


@pytest.mark.parametrize("api,summary", [
    ("B01001_001E", "B01001_E001"),
    ("B01001_026M", "B01001_M026"),
    ("B01001A_009E", "B01001A_E009"),
    ("B05001PR_001M", "B05001PR_M001"),
    ("C17002_001E", "C17002_E001"),
])
def test_variable_translation_both_directions(api, summary):
    assert api_to_summary_variable(api) == summary
    assert summary_to_api_variable(summary) == api


@pytest.mark.parametrize("variable", ["NAME", "B01001_001EA", "../B01001_001E", "B01001_1E"])
def test_invalid_api_variable_raises(variable):
    with pytest.raises(ValueError, match="Unsupported ACS"):
        api_to_summary_variable(variable)


@pytest.mark.parametrize("variable", ["GEO_ID", "B01001_EA001", "B01001_E1"])
def test_invalid_summary_variable_raises(variable):
    with pytest.raises(ValueError, match="Unsupported Summary File"):
        summary_to_api_variable(variable)


@pytest.mark.parametrize("geography,state,county,geoids", [
    ("state", None, None, ["01", "06"]),
    ("state", "CA", None, ["06"]),
    ("county", None, None, ["01003", "06001", "06037", "06073"]),
    ("county", "06", None, ["06001", "06037", "06073"]),
    ("county", "06", "037", ["06037"]),
    ("county", "06", "*", ["06001", "06037", "06073"]),
    ("nation", None, None, [""]),
])
def test_real_geography_filtering(source, download, geography, state, county, geoids):
    frame, provenance = source.fetch(**{
        **REQUEST, "geography": geography, "state_fips": state, "county_fips": county,
    })
    assert frame["GEOID"].tolist() == geoids
    assert list(frame) == ["GEOID", "NAME", "B01003_001E"]
    assert frame["B01003_001E"].dtype == "int64"
    assert frame["NAME"].isna().all()
    assert provenance == Provenance("bulk", POPULATION_URL, 1, False)
    download.assert_called_once_with(POPULATION_URL, stream=True, timeout=15)


def test_real_sentinel_and_include_moe(source, download):
    estimates, _ = source.fetch(**REQUEST)
    with_moe, _ = source.fetch(**{**REQUEST, "include_moe": True})

    assert list(with_moe) == ["GEOID", "NAME", "B01003_001E", "B01003_001M"]
    assert with_moe["B01003_001E"].tolist() == [1628997, 9721138, 3276208]
    assert with_moe["B01003_001M"].isna().all()
    assert with_moe["B01003_001M"].dtype == "float64"
    assert_frame_equal(estimates, with_moe.drop(columns="B01003_001M"))
    assert download.call_count == 1  # New columns are read from the cached raw table.


@pytest.mark.parametrize("geography,geoid", [
    ("tract", "06037000100"), ("block group", "060370001001"),
    ("bg", "060370001001"), ("place", "0644000"),
])
def test_synthetic_subcounty_geographies(source, monkeypatch, geography, geoid):
    # Synthetic adversarial rows, separate from the unmodified Census fixtures.
    body = b"GEO_ID|B01003_E001|B01003_M001\n" + b"\n".join([
        b"1400000US06037000100|10|1", b"1400000US06073000100|20|2",
        b"14000A0US06037000100|99|9", b"1500000US060370001001|5|1",
        b"1500000US060730001001|8|2", b"1600000US0644000|30|3",
        b"1600000US0144000|40|4", b"1400000US06037|999|9",
    ])
    monkeypatch.setattr("requests.get", Mock(return_value=response_for(body)))
    frame, _ = source.fetch(**{
        **REQUEST, "geography": geography,
        "county_fips": None if geography == "place" else "037",
    })
    assert frame["GEOID"].tolist() == [geoid]


@pytest.mark.parametrize("sentinel", [-111111111, -222222222, -333333333,
                                      -444444444, -555555555, -666666666,
                                      -777777777, -888888888, -999999999])
def test_synthetic_sentinels_preserve_valid_negative_values(source, monkeypatch, sentinel):
    body = (f"GEO_ID|B19013_E001|B19013_M001\n"
            f"0500000US06037|{sentinel}|{sentinel}\n"
            "0500000US06073|-42|0\n").encode()
    monkeypatch.setattr("requests.get", Mock(return_value=response_for(body)))
    frame, _ = source.fetch(**{**REQUEST, "variables": "B19013_001E", "include_moe": True})
    assert frame.loc[0, ["B19013_001E", "B19013_001M"]].isna().all()
    assert frame.loc[1, "B19013_001E"] == -42
    assert frame.loc[1, "B19013_001M"] == 0


def test_alias_group_and_table_join_by_geoid(source, download):
    registry = VariableRegistry(groups={"population_and_income": ["B01003_001E", "B19013_001E"]})
    source = BulkFileSource(source.cache_dir, registry=registry, chunksize=2)
    original_get = download.side_effect

    def reordered_table(url, **kwargs):
        if url == INCOME_URL:
            lines = (FIXTURES / "acsdt1y2022-b19013.dat").read_bytes().splitlines()
            return response_for(b"\n".join([lines[0], *reversed(lines[1:])]))
        return original_get(url, **kwargs)

    download.side_effect = reordered_table
    frame, _ = source.fetch(**{**REQUEST, "variables": "population_and_income", "include_moe": True})
    assert list(frame) == ["GEOID", "NAME", "B01003_001E", "B01003_001M", "B19013_001E", "B19013_001M"]
    assert frame["GEOID"].tolist() == ["06001", "06037", "06073"]
    assert frame["B19013_001E"].tolist() == [122159, 82516, 98928]
    assert frame["B19013_001M"].tolist() == [3735, 744, 2263]
    assert download.call_args_list == [
        call(POPULATION_URL, stream=True, timeout=15), call(INCOME_URL, stream=True, timeout=15),
    ]


def test_default_registry_alias_uses_concrete_table(source, monkeypatch):
    body = b"GEO_ID|B01001_E001|B01001_M001\n0500000US06037|9721138|25\n"
    get = Mock(return_value=response_for(body))
    monkeypatch.setattr("requests.get", get)
    frame, _ = source.fetch(**{**REQUEST, "variables": "total_population"})
    assert frame["B01001_001E"].tolist() == [9721138]
    assert get.call_args.args[0].endswith("/acsdt1y2022-b01001.dat")


def test_explicit_moe_and_duplicates_download_once(source, download):
    frame, _ = source.fetch(**{
        **REQUEST, "variables": ["B19013_001M", "B19013_001E", "B19013_001M"], "include_moe": True,
    })
    assert list(frame) == ["GEOID", "NAME", "B19013_001M", "B19013_001E"]
    download.assert_called_once_with(INCOME_URL, stream=True, timeout=15)


@pytest.mark.parametrize("include_moe", [False, True])
@pytest.mark.parametrize("geography", ["state", "county"])
def test_api_shape_parity(source, download, geography, include_moe):
    request = {**REQUEST, "variables": "B19013_001E", "geography": geography,
               "include_moe": include_moe}
    # Build the reference with the actual API response processor, behind a mocked API.
    if geography == "state":
        raw = pd.DataFrame({"NAME": ["California"], "B19013_001E": ["91551"],
                            "B19013_001M": ["471"], "state": ["06"]})
    else:
        raw = pd.DataFrame({"NAME": ["Alameda County, California", "Los Angeles County, California",
                                     "San Diego County, California"],
                            "B19013_001E": ["122159", "82516", "98928"],
                            "B19013_001M": ["3735", "744", "2263"],
                            "state": ["06"] * 3, "county": ["001", "037", "073"]})
    if not include_moe:
        raw = raw.drop(columns="B19013_001M")
    api = Mock(spec=CensusAPI)
    processor = object.__new__(CensusAPI)
    api.fetch_data.return_value = processor._process_response(raw, geography)
    api_frame, _ = ApiSource(api).fetch(**request)
    bulk_frame, _ = source.fetch(**request)

    assert list(bulk_frame) == list(api_frame)
    assert bulk_frame.dtypes.equals(api_frame.dtypes)
    assert_frame_equal(bulk_frame.drop(columns="NAME"), api_frame.drop(columns="NAME"))
    assert bulk_frame["NAME"].isna().all()  # Explicitly deferred name enrichment.
    api.fetch_data.assert_called_once_with(**request)


def test_real_bulk_secondary_serves_after_primary_degrades(source, download):
    api = Mock(spec=CensusAPI)
    api.fetch_data.side_effect = CensusRateLimitError("rate limited")
    frame, provenance = DualSourceCensusClient(
        ApiSource(api), source, AlternationPolicy(max_api_attempts=2),
    ).fetch(**REQUEST)
    assert frame["GEOID"].tolist() == ["06001", "06037", "06073"]
    assert frame["B01003_001E"].tolist() == [1628997, 9721138, 3276208]
    assert provenance == Provenance("bulk", POPULATION_URL, 3, True)
    assert api.fetch_data.call_args_list == [call(**REQUEST)] * 2
    assert download.call_count == 1


def test_cache_key_separates_year_period_and_table(source, download):
    # Reuse a slice's bytes solely to test distinct URL/cache keys, not other vintages' values.
    body = (FIXTURES / "acsdt1y2022-b01003.dat").read_bytes()
    download.side_effect = lambda url, **kwargs: response_for(body, url)
    for year, dataset in [(2022, "acs1"), (2022, "acs5"), (2023, "acs5")]:
        request = {**REQUEST, "year": year, "dataset": dataset}
        source.fetch(**request)
        BulkFileSource(source.cache_dir).fetch(**request)
    assert download.call_args_list == [
        call(POPULATION_URL, stream=True, timeout=15),
        call(f"{BASE}/2022/table-based-SF/data/5YRData/acsdt5y2022-b01003.dat", stream=True, timeout=15),
        call(f"{BASE}/2023/table-based-SF/data/5YRData/acsdt5y2023-b01003.dat", stream=True, timeout=15),
    ]
    assert len(list(source.cache_dir.glob("*.dat"))) == 3


def test_parse_only_requested_columns_in_chunks(source, download, monkeypatch):
    read_csv = Mock(wraps=pd.read_csv)
    monkeypatch.setattr(pd, "read_csv", read_csv)
    source.fetch(**REQUEST)
    assert read_csv.call_args.kwargs["usecols"] == ["GEO_ID", "B01003_E001"]
    assert read_csv.call_args.kwargs["chunksize"] == 2
    assert read_csv.call_args.kwargs["dtype"] is str


@pytest.mark.parametrize("changes,message", [
    ({"dataset": "dec"}, "support acs1/acs5"),
    ({"dataset": "acs5/subject"}, "support acs1/acs5"),
    ({"year": "2022"}, "four-digit integer"),
    ({"year": True}, "four-digit integer"),
    ({"variables": []}, "At least one"),
    ({"variables": "B01003_001EA"}, "Unsupported ACS"),
    ({"geography": "zcta"}, "Unsupported Summary File geography"),
    ({"geography": "invalid"}, "Invalid geography"),
    ({"geography": "nation"}, "does not accept"),
    ({"geography": "state", "county_fips": "037"}, "County filters require"),
    ({"county_fips": "37"}, "three digits"),
    ({"county_fips": "037", "state_fips": None}, "requires state FIPS"),
    ({"geography": "tract", "state_fips": None}, "State FIPS code is required"),
])
def test_invalid_request_raises_before_download(source, download, changes, message):
    with pytest.raises(ValueError, match=message):
        source.fetch(**{**REQUEST, **changes})
    download.assert_not_called()


@pytest.mark.parametrize("kwargs,message", [
    ({"timeout": 0}, "finite and positive"),
    ({"timeout": float("inf")}, "finite and positive"),
    ({"chunksize": 0}, "positive integer"),
    ({"chunksize": True}, "positive integer"),
])
def test_invalid_configuration_raises(kwargs, message):
    with pytest.raises(ValueError, match=message):
        BulkFileSource(**kwargs)


@pytest.mark.parametrize("status", [404, 500])
def test_http_error_propagates_without_caching(source, monkeypatch, status):
    monkeypatch.setattr("requests.get", Mock(return_value=response_for(b"error", status=status)))
    with pytest.raises(HTTPError, match=str(status)):
        source.fetch(**REQUEST)
    assert not list(source.cache_dir.iterdir())


@pytest.mark.parametrize("error_type", [Timeout, ConnectionError])
def test_transport_error_propagates_without_caching(source, monkeypatch, error_type):
    error = error_type("transport failed")
    monkeypatch.setattr("requests.get", Mock(side_effect=error))
    with pytest.raises(error_type, match="transport failed") as raised:
        source.fetch(**REQUEST)
    assert raised.value is error
    assert not list(source.cache_dir.iterdir())


def test_interrupted_download_is_removed_and_retried(source, download):
    response = response_for(b"")

    def interrupted(chunk_size):
        yield b"GEO_ID|B01003_E001"
        raise Timeout("stream interrupted")

    response.iter_content = interrupted
    download.side_effect = [response, response_for((FIXTURES / "acsdt1y2022-b01003.dat").read_bytes())]
    with pytest.raises(Timeout, match="stream interrupted"):
        source.fetch(**REQUEST)
    assert not list(source.cache_dir.iterdir())
    frame, _ = source.fetch(**REQUEST)
    assert len(frame) == 3
    assert download.call_count == 2


@pytest.mark.parametrize("body,message", [
    (b"<html>upstream error</html>", "Usecols do not match"),
    (b"GEO_ID|B19013_E001\n0500000US06037|82516\n", "Usecols do not match"),
    (b"GEO_ID|B01003_E001\n0500000US06037|1\n0500000US06037|2\n", "Duplicate GEOIDs"),
])
def test_malformed_or_duplicate_table_raises(source, monkeypatch, body, message):
    monkeypatch.setattr("requests.get", Mock(return_value=response_for(body)))
    with pytest.raises(ValueError, match=message):
        source.fetch(**REQUEST)


def test_missing_geography_raises(source, download):
    with pytest.raises(CensusAPIError, match="No county rows"):
        source.fetch(**{**REQUEST, "county_fips": "999"})


def test_missing_requested_column_raises(source, download):
    with pytest.raises(ValueError, match="Usecols do not match"):
        source.fetch(**{**REQUEST, "variables": "B01003_002E"})


def test_cache_filesystem_error_propagates(tmp_path, download):
    cache = tmp_path / "not-a-directory"
    cache.write_text("occupied")
    with pytest.raises(FileExistsError):
        BulkFileSource(cache_dir=cache).fetch(**REQUEST)
    download.assert_not_called()


def test_secondary_http_failure_is_not_a_valid_empty_result(source, monkeypatch):
    api = Mock(spec=CensusAPI)
    api.fetch_data.side_effect = Timeout("API timed out")
    monkeypatch.setattr("requests.get", Mock(return_value=response_for(b"missing", status=404)))
    with pytest.raises(HTTPError, match="404"):
        DualSourceCensusClient(ApiSource(api), source).fetch(**REQUEST)
    assert api.fetch_data.call_count == 3


# --- #1385 P2: malformed/corrupt Summary File records must raise, not coerce ---

def _serve(monkeypatch, body: bytes):
    """Serve a crafted .dat body for the population table (no live network)."""
    monkeypatch.setattr(
        "requests.get", Mock(side_effect=lambda url, **kwargs: response_for(body, url))
    )


# Rows use a county GEO_ID so they pass REQUEST's county/state_fips=06 filter
# and reach the numeric parse (the point under test).
@pytest.mark.parametrize("body,exc", [
    # Extra field beyond the header width (corrupt/format-drifted record).
    (b"GEO_ID|B01003_E001\n0500000US06037|123|9721138\n", ValueError),
    # Missing field: a record narrower than its header. The MOE column is
    # unrequested (include_moe=False), so only the width check can catch this
    # -- the empty-cell guard never inspects the padded, unselected column.
    (b"GEO_ID|B01003_E001|B01003_M001\n0500000US06037|123\n", ValueError),
    # Non-numeric estimate token.
    (b"GEO_ID|B01003_E001\n0500000US06037|garbage\n", ValueError),
    # Truncated: empty estimate cell. pd.to_numeric would coerce to NaN.
    (b"GEO_ID|B01003_E001\n0500000US06037|\n", ValueError),
    # Embedded bare CR: pandas treats it as a record boundary. The field count
    # matches the header, so only the control-byte rejection can catch it.
    (b"GEO_ID|B01003_E001|B01003_M001\n0500000US06037|123\r456|25\n", ValueError),
    # Embedded NUL: pandas' C parser truncates the cell at NUL before parsing.
    (b"GEO_ID|B01003_E001\n0500000US06037|123\x00garbage\n", ValueError),
    # Non-finite tokens accepted by pd.to_numeric but invalid as ACS values.
    (b"GEO_ID|B01003_E001\n0500000US06037|inf\n", ValueError),
    (b"GEO_ID|B01003_E001\n0500000US06037|-Infinity\n", ValueError),
    (b"GEO_ID|B01003_E001\n0500000US06037|nan\n", ValueError),
    # Embedded NUL in the HEADER: pandas would truncate the header behind the
    # validator, shifting every downstream column. (The symmetric CR branch of
    # the same guard is exercised by the data-row embedded-CR case above;
    # a header-CR fixture is caught first by pandas' usecols mismatch, so it
    # would not be red-on-revert for this guard specifically.)
    (b"GEO_ID|B01003_E001\x00\n0500000US06037|123\n", ValueError),
    # Duplicate header column: pandas renames the second to `.1`, so a
    # requested column could silently resolve to the wrong data.
    (b"GEO_ID|B01003_E001|B01003_E001\n0500000US06037|25|123\n", ValueError),
    # BOM-masked duplicate: pandas strips the leading UTF-8 BOM before
    # de-duplicating, so the duplicate check must strip it too.
    (b"\xef\xbb\xbfB01003_E001|GEO_ID|B01003_E001\n25|0500000US06037|123\n", ValueError),
    # Quoted delimiter: default pandas quoting would consume "25|123" as one
    # field and shift values; QUOTE_NONE keeps the stray quote in the token so
    # the strict numeric parse rejects it.
    (b'GEO_ID|B01003_M001|B01003_E001|B01003_E002\n0500000US06037|"25|123"|999\n', ValueError),
])
def test_malformed_record_raises(source, monkeypatch, body, exc):
    _serve(monkeypatch, body)
    with pytest.raises(exc):
        source.fetch(**REQUEST)


def test_sentinel_still_coerced_to_nan_after_strict_parse(source, monkeypatch):
    import math
    _serve(monkeypatch, b"GEO_ID|B01003_E001\n0500000US06037|-555555555\n")
    frame, _ = source.fetch(**REQUEST)
    assert math.isnan(frame["B01003_001E"].iloc[0])
