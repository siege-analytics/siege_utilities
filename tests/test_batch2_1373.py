"""Issue #1373 Q5b: validate Census paths after Requests preparation.

The direct separator regressions fail on Batch 1; split escapes fail before
the P1 correction. P2 acceptance regressions catch raw-path over-rejection.
Compatibility controls pin rejection policy and exact fetch URL spelling.
"""

from importlib import import_module
from unittest.mock import Mock, call
from urllib.parse import unquote, urlsplit

import pytest
import requests


CENSUS_HOSTS = [
    "api.census.gov",
    "%61pi.census.gov",
    "api.census.gov.",
    "api.census.gov..",
    "api.census.gov...",
    "%41PI.CENSUS.GOV%2e%2E:443",
]

ENCODED_DATASET_PATHS = [
    pytest.param("/data%2f2023%2facs%2facs5", id="lowercase"),
    pytest.param("/data%2F2023%2Facs%2Facs5", id="uppercase"),
    pytest.param("/data%2f2023%2Facs%2facs5", id="mixed-case"),
    pytest.param("/%2fdata%2f2023%2facs%2facs5", id="leading-encoded-slash"),
    pytest.param(
        "/%64%61%74%61%2f%32%30%32%33%2F%61%63%73%2f%61%63%73%35",
        id="fully-encoded",
    ),
    pytest.param("/data%2f2023/cbp", id="batch1-lowercase-bypass"),
    pytest.param("/%64ata%2F2023/cbp", id="batch1-unreserved-bypass"),
    pytest.param("/data%2ftimeseries%2fgovs%2fschfin", id="yearless"),
    pytest.param("/data%2Ftimeseries", id="yearless-short"),
    pytest.param("/data%2f2023", id="year-only"),
    pytest.param("/data%2f%2f2023%2f%2facs%2facs5", id="encoded-empty-segments"),
    pytest.param("//%2fdata%2F/%2f2023//acs%2facs5%2f", id="mixed-empty-segments"),
    pytest.param("/data%2fdata%2f2023%2facs%2facs5", id="repeated-roots"),
    pytest.param("/data%2fdata%2ftimeseries%2fgovs", id="repeated-yearless-roots"),
    pytest.param("/data%2f%2e%2e%2f2023%2facs%2facs5", id="encoded-dot-dot"),
    pytest.param("/data%2F%2E%2E%2F2023%2Facs%2Facs5", id="uppercase-dot-dot"),
    pytest.param("/data%2f..%2f2023%2facs%2facs5", id="literal-dot-dot"),
    pytest.param("/data%2f.%2f2023%2facs%2facs5", id="literal-dot"),
    pytest.param("/prefix%2f%2e%2e%2fdata%2f2023%2facs%2facs5", id="prefix-dot-dot"),
    pytest.param("/data%2f2023%2facs%2facs5%2f..%2f..%2f..", id="trailing-dot-dot"),
    pytest.param("/prefix%2fdata%2f2023%2facs%2facs5", id="prefixed-dataset"),
    pytest.param("/%2fproxy%2fdata%2f2023%2facs%2facs5", id="decoded-netloc-lookalike"),
]

# The expected paths are literal Requests output after the existing outbound
# normalization. Preparing the raw input would miss these split escapes.
SPLIT_DATASET_PATHS = [
    pytest.param("/%6%34ata/2023/acs/acs5", "/data/2023/acs/acs5/data", id="split-d"),
    pytest.param("/%6%34%61%74%61/2023/acs/acs5", "/data/2023/acs/acs5/data", id="split-encoded-data"),
    pytest.param("/d%6%31ta/2023/acs/acs5", "/data/2023/acs/acs5/data", id="split-a"),
    pytest.param("/%6%34ata%2f2023%2Facs%2facs5", "/data%2F2023%2Facs%2Facs5/data", id="split-d-mixed-separators"),
    pytest.param("/data%2%662023%2%66acs%2%66acs5", "/data%2F2023%2Facs%2Facs5/data", id="split-slashes-lowercase"),
    pytest.param("/data%2%462023%2%46acs%2%46acs5", "/data%2F2023%2Facs%2Facs5/data", id="split-slashes-uppercase"),
    pytest.param("/data%2%662023%2%46acs%2%66acs5", "/data%2F2023%2Facs%2Facs5/data", id="split-slashes-mixed-case"),
    pytest.param("/data%%32f2023%%32Facs%%32facs5", "/data%2F2023%2Facs%2Facs5/data", id="split-slash-first-digit"),
    pytest.param("/data%%32%662023%%32%46acs%%32%66acs5", "/data%2F2023%2Facs%2Facs5/data", id="split-slash-both-digits"),
    pytest.param("/data%2%662023/acs%2Facs5", "/data%2F2023/acs%2Facs5/data", id="mixed-literal-separators"),
    pytest.param("//%6%34ata//2023//acs//acs5/", "/data/2023/acs/acs5/data", id="empty-segments"),
    pytest.param("/data%2%66%2%462023%2%66acs%2%46acs5", "/data%2F%2F2023%2Facs%2Facs5/data", id="encoded-empty-segments"),
    pytest.param("/%2%66data%2%462023/acs/acs5", "/%2Fdata%2F2023/acs/acs5/data", id="leading-encoded-slash"),
    pytest.param("/data%2%66data%2%462023/acs/acs5", "/data%2Fdata%2F2023/acs/acs5/data", id="repeated-roots"),
    pytest.param("/data%2%66timeseries%2%46govs%2%66schfin", "/data%2Ftimeseries%2Fgovs%2Fschfin/data", id="yearless"),
    pytest.param("/prefix%2%66%6%34ata%2%462023/acs/acs5", "/prefix%2Fdata%2F2023/acs/acs5/data", id="prefixed-dataset"),
]

# Literal expected roots freeze Batch-1 output; do not derive them by unquoting.
ACCEPTED_BASES = [
    ("https://api.census.gov", "https://api.census.gov/data"),
    ("https://api.census.gov/", "https://api.census.gov/data"),
    ("https://api.census.gov/data", "https://api.census.gov/data"),
    ("https://api.census.gov/data/", "https://api.census.gov/data"),
    ("https://api.census.gov//data//data/", "https://api.census.gov/data"),
    ("https://api.census.gov//data/", "https://api.census.gov/data"),
    ("https://api.census.gov/%64ata", "https://api.census.gov/data"),
    ("https://api.census.gov//%64ata//data/", "https://api.census.gov/data"),
    ("https://api.census.gov/%64%61%74%61/", "https://api.census.gov/data"),
    ("https://%61pi.census.gov../%64ata/", "https://%61pi.census.gov../data"),
    ("https://api.census.gov/data?key=value#fragment", "https://api.census.gov/data"),
    ("https://proxy/data/census", "https://proxy/data/census/data"),
    ("https://proxy/data/2023/census", "https://proxy/data/2023/census/data"),
    ("https://proxy/2023/gw", "https://proxy/2023/gw/data"),
    ("https://proxy/data/2023/gw", "https://proxy/data/2023/gw/data"),
    ("https://proxy/data/2023/acs/acs5", "https://proxy/data/2023/acs/acs5/data"),
    ("https://proxy../data/timeseries/govs/schfin", "https://proxy../data/timeseries/govs/schfin/data"),
    ("https://proxy/%64ata/%32%30%32%33/census", "https://proxy/data/2023/census/data"),
    ("https://proxy/%7e%61%2D%5F%2e", "https://proxy/~a-_./data"),
    ("https://proxy/data%2f2023%2Facs%2facs5", "https://proxy/data%2f2023%2Facs%2facs5/data"),
    ("https://proxy/%64ata%2F%32%30%32%33/census", "https://proxy/data%2F2023/census/data"),
    ("https://proxy/%2f%2e%2e%2Fdata%2f2023", "https://proxy/%2f..%2Fdata%2f2023/data"),
    ("https://proxy/data/%2fdata", "https://proxy/data/%2fdata/data"),
    ("https://proxy/%252f/%3F/%23/%25/%c3%a9/%zz", "https://proxy/%252f/%3F/%23/%25/%c3%a9/%zz/data"),
    ("https://api.census.gov.proxy/data%2f2023", "https://api.census.gov.proxy/data%2f2023/data"),
    ("https://%70roxy../%64ata%2f2023", "https://%70roxy../data%2f2023/data"),
    ("https://api.census.gov/data%252f2023%252facs%252facs5", "https://api.census.gov/data%252f2023%252facs%252facs5/data"),
    ("https://api.census.gov/data%252F2023%252facs%252Facs5", "https://api.census.gov/data%252F2023%252facs%252Facs5/data"),
    ("https://api.census.gov/%2564ata%2f2023", "https://api.census.gov/%2564ata%2f2023/data"),
    ("https://api.census.gov/proxy%2fcensus", "https://api.census.gov/proxy%2fcensus/data"),
    ("https://api.census.gov/%2fdata", "https://api.census.gov/%2fdata/data"),
    ("https://api.census.gov/data%2fdata", "https://api.census.gov/data%2fdata/data"),
    ("https://api.census.gov/data%2f", "https://api.census.gov/data%2f/data"),
    ("https://api.census.gov/%2f%2F", "https://api.census.gov/%2f%2F/data"),
    ("https://api.census.gov/proxy/%2e%2e/data", "https://api.census.gov/proxy/../data"),
    ("https://proxy/%6%34ata/2023/acs/acs5", "https://proxy/%64ata/2023/acs/acs5/data"),
    ("https://proxy/data%2%662023%2%46acs%2%66acs5", "https://proxy/data%2f2023%2Facs%2facs5/data"),
    ("https://api.census.gov/%6%34ata", "https://api.census.gov/%64ata/data"),
    ("https://api.census.gov/data%2%66data", "https://api.census.gov/data%2fdata/data"),
    ("https://api.census.gov/data%25252f2023", "https://api.census.gov/data%25252f2023/data"),
    ("https://api.census.gov/data%C0%AF2023/acs/acs5", "https://api.census.gov/data%C0%AF2023/acs/acs5/data"),
    ("https://api.census.gov/data%E0%80%AF2023/acs/acs5", "https://api.census.gov/data%E0%80%AF2023/acs/acs5/data"),
    ("https://api.census.gov/data%EF%BC%8F2023/acs/acs5", "https://api.census.gov/data%EF%BC%8F2023/acs/acs5/data"),
    ("https://api.census.gov/data／2023/acs/acs5", "https://api.census.gov/data／2023/acs/acs5/data"),
    ("https://api.census.gov/data+2023/acs/acs5", "https://api.census.gov/data+2023/acs/acs5/data"),
    ("https://api.census.gov/data%2%2023/acs/acs5", "https://api.census.gov/data%2%2023/acs/acs5/data"),
]

# Requests resolves dot segments and protects escapes when a malformed escape
# is present. Raw separator decoding must not override the prepared path.
PREPARED_NON_DATASET_PATHS = [
    pytest.param("/data%2f2023/..", "/data%2f2023/../data", "/data", id="literal-dot-dot"),
    pytest.param("/data%2f2023/%2e%2e", "/data%2f2023/../data", "/data", id="encoded-dot-dot"),
    pytest.param(
        "/data%2f2023/%zz", "/data%2f2023/%zz/data",
        "/data%252F2023/%25zz/data", id="malformed-escape",
    ),
    pytest.param("/data%2F2023/%2E%2E", "/data%2F2023/../data", "/data", id="uppercase-dot-dot"),
    pytest.param("/data%2f2023/.%2e", "/data%2f2023/../data", "/data", id="mixed-dot-dot-first"),
    pytest.param("/data%2f2023/%2e.", "/data%2f2023/../data", "/data", id="mixed-dot-dot-second"),
    pytest.param(
        "/data%2F2023/%zz", "/data%2F2023/%zz/data",
        "/data%252F2023/%25zz/data", id="uppercase-malformed-escape",
    ),
    pytest.param(
        "/data%2f2023%2facs%2facs5/%zz", "/data%2f2023%2facs%2facs5/%zz/data",
        "/data%252F2023%252Facs%252Facs5/%25zz/data", id="dataset-malformed-escape",
    ),
    pytest.param(
        "/data%2ftimeseries%2fgovs%2fschfin/%zz", "/data%2ftimeseries%2fgovs%2fschfin/%zz/data",
        "/data%252Ftimeseries%252Fgovs%252Fschfin/%25zz/data", id="timeseries-malformed-escape",
    ),
]

LEGACY_REJECTED_PATHS = [
    "/data/2023/acs/acs5",
    "/data/2023/cbp",
    "/data/2023/custom/a/b",
    "/data/2023",
    "/data/timeseries/govs/schfin",
    "/data/timeseries",
    "//data//data/timeseries/govs/schfin",
    "/%64ata/2023/cbp",
    "/data/%32%30%32%33/cbp",
    "/data/%2e%2e/2023/acs/acs5",
    # Decoding must not erase a component that Batch 1 already rejected.
    "/data/%2f",
    "/data/%2f%2F",
    "/data/%2fdata",
    "/data/data%2fdata",
    "/data/data%2f",
]


@pytest.mark.parametrize("host", CENSUS_HOSTS)
@pytest.mark.parametrize("path", ENCODED_DATASET_PATHS)
def test_encoded_separator_dataset_raises_before_http(monkeypatch, host, path):
    """Every parameter is a previously accepted encoded dataset path."""
    census = import_module("siege_utilities.geo.census.catalog_populator")
    request = Mock(side_effect=AssertionError("dataset URL must fail before HTTP"))
    monkeypatch.setattr(census.requests, "get", request)
    with pytest.raises(ValueError, match="full dataset path.*Pass the API root"):
        census.CensusCatalogPopulator(base_url=f"https://{host}{path}")
    request.assert_not_called()


@pytest.mark.parametrize("host", CENSUS_HOSTS)
@pytest.mark.parametrize("path,wire_path", SPLIT_DATASET_PATHS)
def test_split_escape_dataset_raises_before_http(monkeypatch, host, path, wire_path):
    """Pin Requests' output, then reject every pre-correction Batch-2 smuggle."""
    census = import_module("siege_utilities.geo.census.catalog_populator")
    request = Mock(side_effect=AssertionError("dataset URL must fail before HTTP"))
    monkeypatch.setattr(census.requests, "get", request)

    # Proxies accept these prefixes and preserve the same outbound path bytes.
    proxy = census.CensusCatalogPopulator(base_url=f"https://proxy{path}")
    candidate = f"https://{host}{urlsplit(proxy.base_url).path}"
    prepared = requests.Request("GET", candidate).prepare()
    assert prepared.path_url == wire_path
    for leaf in ("variables", "groups"):
        fetch = requests.Request("GET", f"{candidate}/2023/acs/acs5/{leaf}.json").prepare()
        assert fetch.path_url == f"{wire_path}/2023/acs/acs5/{leaf}.json"

    with pytest.raises(ValueError, match="full dataset path.*Pass the API root"):
        census.CensusCatalogPopulator(base_url=f"https://{host}{path}")
    request.assert_not_called()


@pytest.mark.parametrize("escape", ["%252f", "%252F"])
def test_double_encoded_separator_stays_literal_on_wire(escape):
    census = import_module("siege_utilities.geo.census.catalog_populator")
    path = f"/data{escape}2023{escape}acs{escape}acs5/data"
    populator = census.CensusCatalogPopulator(base_url=f"https://api.census.gov{path}")
    for leaf in ("variables", "groups"):
        suffix = f"/2023/acs/acs5/{leaf}.json"
        prepared = requests.Request("GET", f"{populator.base_url}{suffix}").prepare()
        # Requests retains %25 on the wire. One path interpretation yields a
        # literal %2f (or %2F); a recursive decoder would wrongly create '/'.
        assert prepared.path_url == f"{path}{suffix}"
        assert unquote(prepared.path_url) == f"{path.replace('%25', '%')}{suffix}"


@pytest.mark.parametrize("base,expected_root", ACCEPTED_BASES)
def test_accepted_fetch_urls_match_batch1_control(monkeypatch, base, expected_root):
    """Validate real populate/fetch composition with only HTTP replaced."""
    census = import_module("siege_utilities.geo.census.catalog_populator")
    response = Mock()
    response.json.return_value = {"variables": {}, "groups": []}
    request = Mock(return_value=response)
    monkeypatch.setattr(census.requests, "get", request)

    populator = census.CensusCatalogPopulator(base_url=base, timeout=17)
    populator.populate("acs5", 2023)

    assert populator.base_url == expected_root
    assert request.call_args_list == [
        call(f"{expected_root}/2023/acs/acs5/{leaf}.json", timeout=17)
        for leaf in ["variables", "groups"]
    ]
    assert response.raise_for_status.call_count == 2


@pytest.mark.parametrize("host", CENSUS_HOSTS)
@pytest.mark.parametrize("path,normalized_path,wire_path", PREPARED_NON_DATASET_PATHS)
def test_prepared_non_dataset_accepts_with_original_fetch_urls(
    monkeypatch, host, path, normalized_path, wire_path,
):
    """Pin origin/develop accepts and both fetch URLs despite raw dataset shapes."""
    census = import_module("siege_utilities.geo.census.catalog_populator")
    response = Mock()
    response.json.return_value = {"variables": {}, "groups": []}
    request = Mock(return_value=response)
    monkeypatch.setattr(census.requests, "get", request)

    expected_root = f"https://{host}{normalized_path}"
    assert requests.Request("GET", expected_root).prepare().path_url == wire_path
    populator = census.CensusCatalogPopulator(base_url=f"https://{host}{path}", timeout=17)
    request.assert_not_called()
    assert populator.base_url.encode("utf-8") == expected_root.encode("utf-8")
    populator.populate("acs5", 2023)

    suffixes = [f"/2023/acs/acs5/{leaf}.json" for leaf in ("variables", "groups")]
    assert request.call_args_list == [call(f"{expected_root}{suffix}", timeout=17) for suffix in suffixes]
    for fetch_call, suffix in zip(request.call_args_list, suffixes):
        url = fetch_call.args[0]
        assert url.encode("utf-8") == f"{expected_root}{suffix}".encode("utf-8")
        assert requests.Request("GET", url).prepare().path_url == f"{wire_path}{suffix}"
    assert response.raise_for_status.call_count == 2


@pytest.mark.parametrize("host", CENSUS_HOSTS)
@pytest.mark.parametrize("path", LEGACY_REJECTED_PATHS)
def test_legacy_dataset_raises_before_http_control(monkeypatch, host, path):
    census = import_module("siege_utilities.geo.census.catalog_populator")
    request = Mock(side_effect=AssertionError("dataset URL must fail before HTTP"))
    monkeypatch.setattr(census.requests, "get", request)
    with pytest.raises(ValueError, match="full dataset path.*Pass the API root"):
        census.CensusCatalogPopulator(base_url=f"https://{host}{path}")
    request.assert_not_called()
