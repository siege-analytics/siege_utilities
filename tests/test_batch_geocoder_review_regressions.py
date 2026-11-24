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
    # Exact message, naming the caller ID and no address text (#1697); a
    # substring check could pass on a random library ID.
    expected = {
        "nominatim": "Nominatim geocode failed for bad: OSError",
        "tamu": "TAMU geocode failed for bad: RuntimeError",
    }[backend.backend_name]
    assert r.errors == [expected]                # failed row reported, genuine no-match not


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
    # The first column is the library-assigned batch ID, not the caller ID (#1410).
    assert [row[1:] for row in rows] == [["1 Main St", "", "MA", "02134"]]
    assert rows[0][0] != "0"


@pytest.mark.parametrize("args, expected", [
    (("1 George St", "Sydney", "NSW", 2000, "Australia"), "1 George St, Sydney, NSW, 2000, Australia"),
    (("Rue de la Loi 16", "Brussels", None, 1000, "Belgium"), "Rue de la Loi 16, Brussels, 1000, Belgium"),
    (("Karl Johans gate 1", "Oslo", None, 150, "Norway"), "Karl Johans gate 1, Oslo, 150, Norway"),
    (("1 Connaught Place", "New Delhi", "DL", 110001, "India"), "1 Connaught Place, New Delhi, DL, 110001, India"),
    (("1 Chome", "Chiyoda", "Tokyo", 1000001, "Japan"), "1 Chome, Chiyoda, Tokyo, 1000001, Japan"),
    (("1 George St", "Sydney", "NSW", 2000.0, "Australia"), "1 George St, Sydney, NSW, 2000, Australia"),
])
def test_concatenate_keeps_non_us_postal_codes_unpadded(args, expected):
    # Only US ZIPs get leading zeros restored; other countries' codes keep their digits.
    assert concatenate_addresses(*args) == expected


@pytest.mark.parametrize("country", [None, "", "US", "us", "USA", "United States", "united states"])
def test_concatenate_pads_us_and_unspecified_zip(country):
    assert concatenate_addresses("1 Main St", "Boston", "MA", 2134, country) == ", ".join(
        part for part in ("1 Main St", "Boston", "MA", "02134", country) if part
    )


def test_composite_keeps_non_string_backend_errors():
    # A third-party backend that appends an exception object to errors must not
    # make the composite raise TypeError and lose the batch.
    from siege_utilities.geo.providers.batch_geocoder import (
        BatchGeocoder,
        BatchGeocodingResult,
        GeocodingResult,
        MatchQuality,
    )

    failure = RuntimeError("backend failure")

    class ExceptionInErrors(BatchGeocoder):
        @property
        def backend_name(self):
            return "third_party"

        def geocode(self, addresses):
            rows = normalize_addresses(addresses)
            return BatchGeocodingResult(
                results=[
                    GeocodingResult(
                        input_id=row.input_id, input_address=row.one_line,
                        match_quality=MatchQuality.NO_MATCH.value, backend=self.backend_name,
                    )
                    for row in rows
                ],
                backend=self.backend_name,
                errors=[failure],
            )

    result = CompositeBatchGeocoder([ExceptionInErrors()]).geocode([{"street": "1 Main St", "id": "a"}])
    assert result.total == 1
    assert result.results[0].input_id == "a"
    assert failure in result.errors
