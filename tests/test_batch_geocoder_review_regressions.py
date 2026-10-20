import csv
from unittest.mock import Mock

import pandas as pd
import pytest

from siege_utilities.geo.geocoding_core import concatenate_addresses
from siege_utilities.geo.providers import census_geocoder
from siege_utilities.geo.providers.batch_geocoder import normalize_addresses
from siege_utilities.geo.providers.composite_geocoder import CompositeBatchGeocoder
from siege_utilities.geo.providers.nominatim_batch import NominatimBatchGeocoder
from siege_utilities.geo.providers.tamu_batch import TAMUBatchGeocoder


def _nominatim():
    g = NominatimBatchGeocoder(rate_limit=0.0)

    def req(query):
        if query.startswith("2 Elm St"):
            raise OSError("simulated HTTP 503")
        return None  # genuine no-match for every other row

    g._nominatim_request = req
    return g


def _tamu():
    g = TAMUBatchGeocoder(api_key="test-key", rate_limit=0.0)

    def req(addr):
        if addr.street == "2 Elm St":
            raise RuntimeError("TAMU request failed: simulated")
        return None

    g._tamu_request = req
    return g


@pytest.mark.parametrize("make", [_nominatim, _tamu])
@pytest.mark.parametrize("composite", [False, True])
def test_per_row_failure_is_reported_and_distinguishable(make, composite):
    backend = make()
    g = CompositeBatchGeocoder([backend]) if composite else backend
    r = g.geocode([{"street": "1 Main St", "id": "ok"}, {"street": "2 Elm St", "id": "bad"}])
    assert r.total == 2
    assert len(r.errors) == 1, r.errors          # failed row reported, genuine no-match not
    assert "bad" in r.errors[0]
    assert "2 Elm St" not in r.errors[0]         # no address PII (#1697)


def test_pd_na_is_missing_in_normalize():
    a = normalize_addresses([{"street": "1 Main St", "city": pd.NA, "zip": pd.NA}])[0]
    assert (a.city, a.zipcode) == ("", "")


def test_pd_na_is_missing_in_concatenate():
    assert concatenate_addresses("1 Main St", pd.NA, "MA", pd.NA) == "1 Main St, MA"


@pytest.mark.parametrize("value", [21341234, 21341234.0])
def test_numeric_zip_plus4_restores_leading_zero(value):
    assert normalize_addresses([{"zip": value}])[0].zipcode.replace("-", "") == "021341234"


def test_concatenate_numeric_postal_code_restores_leading_zero():
    assert concatenate_addresses("1 Main St", "Boston", "MA", 2134) == "1 Main St, Boston, MA, 02134"


def test_geocode_batch_direct_dict_path_normalizes_zip(monkeypatch):
    rows = []

    def addressbatch(path, **kw):
        with open(path, newline="") as f:
            rows.extend(csv.reader(f))
        return []

    monkeypatch.setattr(census_geocoder, "_get_geocoder",
                        lambda v: Mock(addressbatch=Mock(side_effect=addressbatch)))
    census_geocoder.geocode_batch_chunked(
        [{"id": 0, "street": "1 Main St", "city": float("nan"), "state": "MA", "zipcode": 2134.0}])
    assert rows == [["0", "1 Main St", "", "MA", "02134"]]
