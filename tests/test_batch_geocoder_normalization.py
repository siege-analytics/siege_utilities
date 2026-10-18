"""Regression coverage for CSV-derived addresses and per-row failures (#1526)."""

import csv
import io
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from siege_utilities.geo.geocoding_core import concatenate_addresses
from siege_utilities.geo.providers import census_geocoder
from siege_utilities.geo.providers.batch_geocoder import (
    AddressInput,
    GeocodingResult,
    MatchQuality,
    normalize_addresses,
)
from siege_utilities.geo.providers.census_batch import CensusBatchGeocoder
from siege_utilities.geo.providers.composite_geocoder import CompositeBatchGeocoder
from siege_utilities.geo.providers.nominatim_batch import NominatimBatchGeocoder
from siege_utilities.geo.providers.tamu_batch import TAMUBatchGeocoder


@pytest.fixture
def csv_records():
    return pd.read_csv(io.StringIO(
        "street,city,state,zip\n"
        "1 Main St,Boston,MA,02134\n"
        "2 Elm St,Boston,MA,\n"
    )).to_dict("records")


@pytest.mark.parametrize("value", [2134, 2134.0, np.int64(2134), np.float32(2134)])
@pytest.mark.parametrize("key", ["zip", "zipcode"])
def test_numeric_zip_restores_leading_zero(value, key):
    assert normalize_addresses([{key: value}])[0].zipcode == "02134"


@pytest.mark.parametrize("value", [None, float("nan"), np.float32("nan")])
def test_missing_fields_become_empty_strings(value):
    address = normalize_addresses([dict.fromkeys(
        ["street", "city", "state", "zip", "id"], value,
    )])[0]
    assert vars(address) == dict.fromkeys(
        ["street", "city", "state", "zipcode", "input_id"], "",
    )
    assert address.one_line == ""


@pytest.mark.parametrize("zipcode", ["", "02134", "02134-1234", "2134", "2134.0"])
def test_string_zip_is_preserved_verbatim(zipcode):
    assert normalize_addresses([{"zip": zipcode}])[0].zipcode == zipcode


def test_all_dictionary_fields_are_coerced_to_strings():
    address = normalize_addresses([{
        "address": 123, "city": 456, "state": 78, "zip": 2134.0, "input_id": 0,
    }])[0]
    assert vars(address) == {
        "street": "123", "city": "456", "state": "78",
        "zipcode": "02134", "input_id": "0",
    }


@pytest.mark.parametrize("offset", [0, 1, 2])
def test_mixed_input_types_are_handled_independently(offset):
    ready = AddressInput(street="3 Oak St", input_id="ready")
    inputs = [{"street": "2 Elm St", "zip": 2134.0}, "1 Main St, Boston MA", ready]
    inputs = inputs[offset:] + inputs[:offset]
    result = normalize_addresses(inputs)
    assert len(result) == len(inputs)
    assert all(isinstance(address, AddressInput) for address in result)
    for index, original in enumerate(inputs):
        if isinstance(original, dict):
            assert result[index].zipcode == "02134"
            assert result[index].input_id == str(index)
        elif isinstance(original, str):
            assert result[index].street == original
            assert result[index].input_id == str(index)
        else:
            assert result[index] is ready


def test_unsupported_element_after_string_raises_type_error():
    with pytest.raises(TypeError, match="Unsupported address type"):
        normalize_addresses(["1 Main St", 42])


@pytest.mark.parametrize("value", [2134.0, float("nan"), None, pd.NA, ["MA"]])
def test_one_line_ignores_non_string_components(value):
    address = AddressInput(street="1 Main St", city=value, state="", zipcode="02134")
    assert address.one_line == "1 Main St, 02134"


@pytest.fixture(params=["nominatim", "tamu"])
def stubbed_backend(request, monkeypatch):
    """Reject the blank-ZIP row and match other rows without network requests."""
    if request.param == "nominatim":
        backend = NominatimBatchGeocoder(rate_limit=0.0)

        def geocode(query):
            if query.startswith("2 Elm St"):
                raise ValueError("stub rejects the blank-ZIP row")
            return (42.36, -71.06)

        method = "_nominatim_request"
    else:
        backend = TAMUBatchGeocoder(api_key="test-key", rate_limit=0.0)

        def geocode(address):
            if address.street == "2 Elm St":
                raise ValueError("stub rejects the blank-ZIP row")
            return GeocodingResult(
                input_address=address.one_line,
                input_id=address.input_id,
                lat=42.36,
                lon=-71.06,
                match_quality=MatchQuality.EXACT.value,
                backend="tamu",
            )

        method = "_tamu_request"
    stub = Mock(side_effect=geocode)
    monkeypatch.setattr(backend, method, stub)
    return backend, stub


@pytest.mark.parametrize("composite", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_csv_records_keep_one_result_per_row(csv_records, stubbed_backend, composite, reverse):
    backend, stub = stubbed_backend
    geocoder = CompositeBatchGeocoder([backend]) if composite else backend
    records = list(reversed(csv_records)) if reverse else csv_records

    result = geocoder.geocode(records)

    assert result.total == len(records)
    assert [row.input_id for row in result.results] == ["0", "1"]
    assert [row.matched for row in result.results] == ([False, True] if reverse else [True, False])
    assert all(row.backend == backend.backend_name for row in result.results)
    by_street = {row.input_address.split(",")[0]: row for row in result.results}
    assert by_street["1 Main St"].input_address == "1 Main St, Boston, MA, 02134"
    assert by_street["2 Elm St"].input_address == "2 Elm St, Boston, MA"
    assert stub.call_count == 2


def test_query_construction_failure_is_confined_to_one_row(stubbed_backend):
    class BrokenQuery(AddressInput):
        @property
        def one_line(self):
            raise TypeError("cannot construct this query")

    backend, stub = stubbed_backend
    result = backend.geocode([
        BrokenQuery(input_id="bad"),
        AddressInput(street="1 Main St", zipcode="02134", input_id="good"),
    ])

    assert result.total == 2
    assert [row.input_id for row in result.results] == ["bad", "good"]
    assert [row.matched for row in result.results] == [False, True]
    assert result.results[0].input_address == ""
    assert stub.call_count == 1


def test_census_csv_preserves_zip_from_pandas(csv_records, monkeypatch):
    submitted_rows = []

    def addressbatch(path, **kwargs):
        with open(path, newline="") as submitted:
            submitted_rows.extend(csv.reader(submitted))
        return []

    client = Mock(addressbatch=Mock(side_effect=addressbatch))
    monkeypatch.setattr(census_geocoder, "_get_geocoder", lambda vintage: client)

    result = CensusBatchGeocoder().geocode(csv_records)

    assert result.errors == []
    assert result.total == len(csv_records)
    assert submitted_rows == [
        ["0", "1 Main St", "Boston", "MA", "02134"],
        ["1", "2 Elm St", "Boston", "MA", ""],
    ]


@pytest.mark.parametrize("missing", [None, float("nan"), np.float32("nan")])
def test_concatenate_addresses_skips_missing_components(missing):
    assert concatenate_addresses("1 Main St", missing, "MA", missing, missing) == "1 Main St, MA"
    assert concatenate_addresses(missing, missing, missing, missing, missing) == ""


def test_concatenate_addresses_retains_non_missing_values():
    assert concatenate_addresses(" 1 Main St ", "Boston", "MA", "02134-1234", 0) == (
        "1 Main St, Boston, MA, 02134-1234, 0"
    )
