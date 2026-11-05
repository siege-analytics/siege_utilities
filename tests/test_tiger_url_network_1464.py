"""#1464: opt-in network check that builder-produced TIGER URLs exist.

Run with ``pytest -m integration --no-cov tests/test_tiger_url_network_1464.py``.
Each case builds a URL with the real ``CensusDirectoryDiscovery`` (live
directory listings) and sends a HEAD request to www2.census.gov. Coverage is
one URL per buildable catalog type for 2010, 2019 and 2023. Types that are not
listed for a vintage, or that the builder refuses by design (per-county
layers, 2010 VTD), are not sampled; offline tests cover those refusals.

Census rate-limits bursts with HTTP 429. Requests are spaced and retried with
backoff; a URL still rate-limited after the retries is skipped, not failed,
because 429 says nothing about whether the file exists.
"""

import time

import pytest
import requests

from siege_utilities.geo.spatial_data import CensusDirectoryDiscovery

pytestmark = pytest.mark.integration

# Layers that need a particular state to name a published file.
STATE_FOR = {"anrc": "02", "concity": "13", "submcd": "72"}
# National-only layers are requested without a state.
NATIONAL = {
    "state", "county", "zcta", "cbsa", "csa", "metdiv", "necta", "nectadiv",
    "cnecta", "aiannh", "ttract", "tbg", "uac", "rails",
}

COMMON = [
    "state", "county", "cousub", "tract", "block_group", "block", "place",
    "sldu", "sldl", "zcta", "cbsa", "csa", "metdiv", "aiannh", "ttract", "tbg",
    "elsd", "scsd", "unsd", "anrc", "concity", "uac", "rails",
]
BY_YEAR = {
    2010: COMMON + ["cd", "cd111", "necta", "nectadiv", "cnecta", "submcd"],
    2019: COMMON + ["cd", "cd116", "necta", "nectadiv", "cnecta", "submcd"],
    # 2022+ congressional districts are per state only.
    2023: COMMON + ["cd", "cd118", "tabblock20"],
}
CD_STATE_FROM = 2022


def _state(year, layer):
    if layer in STATE_FOR:
        return STATE_FOR[layer]
    if layer in NATIONAL:
        return None
    if layer.startswith("cd"):
        return "06" if year >= CD_STATE_FROM else None
    return "01" if layer == "block" else "06"


CASES = [(year, layer, _state(year, layer)) for year, layers in BY_YEAR.items() for layer in layers]
# ANRC without a state resolves to the Alaska file.
CASES.append((2019, "anrc", None))


@pytest.fixture(scope="module")
def discovery():
    # One instance so the live directory listing for each year is fetched once.
    return CensusDirectoryDiscovery(timeout=30)


def _head(url, attempts=6, spacing=1.0):
    time.sleep(spacing)
    for attempt in range(attempts):
        response = requests.head(url, timeout=30, allow_redirects=True)
        if response.status_code != 429:
            return response.status_code
        time.sleep(10 * (attempt + 1))
    return 429


@pytest.mark.parametrize("year,layer,state", CASES, ids=lambda v: str(v))
def test_built_tiger_url_exists(discovery, year, layer, state):
    url = discovery.construct_download_url(year, layer, state_fips=state)
    status = _head(url)
    if status == 429:
        pytest.skip(f"Census still rate-limiting after retries: {url}")
    assert status == 200, f"{layer} {year} {state}: {url} -> {status}"
