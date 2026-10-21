"""Regression tests for #1410; all services are local backend stubs."""

import csv
from copy import deepcopy
from dataclasses import replace

import pytest

from siege_utilities.geo.providers import census_geocoder
from siege_utilities.geo.providers.batch_geocoder import (
    AddressInput,
    BatchGeocoder,
    BatchGeocodingResult,
    GeocodingResult,
)
from siege_utilities.geo.providers.census_batch import CensusBatchGeocoder
from siege_utilities.geo.providers.composite_geocoder import CompositeBatchGeocoder


class ReorderingBackend(BatchGeocoder):
    backend_name = "stub"

    def __init__(self, drop=None, errors=()):
        self.drop = drop
        self.errors = list(errors)
        self.submitted = []

    def geocode(self, addresses):
        self.submitted = list(addresses)
        return BatchGeocodingResult(
            backend=self.backend_name,
            errors=self.errors,
            results=[
                GeocodingResult(
                    input_id=addr.input_id,
                    input_address=addr.one_line,
                    lat=float(addr.street),
                    lon=-float(addr.street),
                    match_quality="exact",
                    backend=self.backend_name,
                )
                for addr in reversed(addresses)
                if addr.street != self.drop
            ],
        )


class CensusAPIStub:
    """Echo the CSV IDs as Census does, with coordinates keyed by street."""

    def __init__(self, failing_call=None, drop=None):
        self.failing_call = failing_call
        self.drop = drop
        self.calls = []

    def addressbatch(self, path, returntype):
        with open(path, newline="") as stream:
            rows = list(csv.reader(stream))
        self.calls.append(rows)
        if len(self.calls) == self.failing_call:
            raise RuntimeError("chunk timed out")
        return [
            {
                "id": row[0], "address": row[1], "parsed": row[1],
                "match": True, "matchtype": "Exact",
                "lat": float(row[1]), "lon": -float(row[1]),
            }
            for row in reversed(rows)
            if row[1] != self.drop
        ]


def addresses(ids):
    return [{"street": str(i + 1), "id": caller_id} for i, caller_id in enumerate(ids)]


def test_reversed_backend_results_land_on_the_correct_input():
    """Ticket Falsifier: a reversed response must not swap coordinates."""
    backend = ReorderingBackend()
    inputs = addresses(["a", "b", "c"])
    result = CompositeBatchGeocoder([backend]).geocode(inputs)

    assert [row.lat for row in result.results] == [1.0, 2.0, 3.0]
    assert [row.input_id for row in result.results] == ["a", "b", "c"]
    assert not result.errors
    assert {addr.input_id for addr in backend.submitted}.isdisjoint({"a", "b", "c"})


def test_dropped_backend_row_never_shifts_another_address():
    result = CompositeBatchGeocoder([ReorderingBackend(drop="2")]).geocode(
        addresses(["a", "b", "c"])
    )

    assert [row.lat for row in result.results] == [1.0, None, 3.0]
    assert not result.results[1].matched
    assert [row.input_id for row in result.results] == ["a", "b", "c"]
    assert result.errors


def test_backend_error_list_is_preserved_even_when_rows_match():
    result = CompositeBatchGeocoder([
        ReorderingBackend(errors=["backend warning"]),
    ]).geocode(addresses(["a"]))

    assert result.matched_count == 1
    assert any("backend warning" in error for error in result.errors)


@pytest.mark.parametrize("composite", [False, True])
@pytest.mark.parametrize("failing_call", [1, 2, 3])
def test_failed_chunk_preserves_other_chunks_and_is_an_error(monkeypatch, composite, failing_call):
    api = CensusAPIStub(failing_call=failing_call)
    monkeypatch.setattr(census_geocoder, "_get_geocoder", lambda vintage: api)
    backend = CensusBatchGeocoder(chunk_size=2)
    geocoder = CompositeBatchGeocoder([backend]) if composite else backend

    result = geocoder.geocode(addresses(["same"] * 6))

    assert len(api.calls) == 3
    assert result.total == 6
    assert result.matched_count == 4
    assert any("chunk timed out" in error for error in result.errors)
    for i, row in enumerate(result.results):
        assert row.input_id == "same"
        if i // 2 == failing_call - 1:
            assert row.match_quality == "error"
            assert not row.matched
            assert row.lat is None
        else:
            assert row.matched
            assert row.lat == float(i + 1)


@pytest.mark.parametrize("entrypoint", ["census", "batch", "composite"])
def test_duplicate_and_blank_caller_ids_get_distinct_response_rows(monkeypatch, entrypoint):
    api = CensusAPIStub()
    monkeypatch.setattr(census_geocoder, "_get_geocoder", lambda vintage: api)
    inputs = addresses(["duplicate", "duplicate", "", ""])
    original = deepcopy(inputs)
    if entrypoint == "census":
        rows = census_geocoder.geocode_batch(inputs)
    elif entrypoint == "batch":
        rows = CensusBatchGeocoder().geocode(inputs).results
    else:
        rows = CompositeBatchGeocoder([CensusBatchGeocoder()]).geocode(inputs).results

    assert [row.lat for row in rows] == [1.0, 2.0, 3.0, 4.0]
    assert [row.input_id for row in rows] == ["duplicate", "duplicate", "", ""]
    submitted_ids = [row[0] for row in api.calls[0]]
    assert len(set(submitted_ids)) == 4
    assert set(submitted_ids).isdisjoint({"duplicate", ""})
    assert inputs == original


def test_missing_caller_ids_do_not_collapse(monkeypatch):
    api = CensusAPIStub()
    monkeypatch.setattr(census_geocoder, "_get_geocoder", lambda vintage: api)
    rows = census_geocoder.geocode_batch([{"street": "1"}, {"street": "2"}])

    assert [row.lat for row in rows] == [1.0, 2.0]
    assert [row.input_id for row in rows] == ["", ""]


def test_one_internal_id_is_threaded_from_composite_to_census_csv(monkeypatch):
    api = CensusAPIStub()
    monkeypatch.setattr(census_geocoder, "_get_geocoder", lambda vintage: api)

    class RecordingCensus(CensusBatchGeocoder):
        def geocode(self, inputs):
            self.ids = [addr.input_id for addr in inputs]
            return super().geocode(inputs)

    backend = RecordingCensus(chunk_size=1)
    repeated_input = AddressInput(street="1", input_id="caller")
    result = CompositeBatchGeocoder([backend]).geocode([repeated_input, repeated_input])

    assert backend.ids == [call[0][0] for call in api.calls]
    assert len(set(backend.ids)) == 2
    assert "caller" not in backend.ids
    assert [row.input_id for row in result.results] == ["caller", "caller"]
    assert repeated_input.input_id == "caller"


def test_fallback_retries_only_failed_rows_with_the_same_internal_ids(monkeypatch):
    api = CensusAPIStub(failing_call=2)
    monkeypatch.setattr(census_geocoder, "_get_geocoder", lambda vintage: api)
    fallback = ReorderingBackend()
    result = CompositeBatchGeocoder([
        CensusBatchGeocoder(chunk_size=2), fallback,
    ]).geocode(addresses(["same"] * 6))

    assert [row.lat for row in result.results] == [1., 2., 3., 4., 5., 6.]
    assert [addr.street for addr in fallback.submitted] == ["3", "4"]
    assert [addr.input_id for addr in fallback.submitted] == [row[0] for row in api.calls[1]]
    assert [row.input_id for row in result.results] == ["same"] * 6
    assert any("chunk timed out" in error for error in result.errors)


@pytest.mark.parametrize("nested", [False, True])
def test_fallback_no_match_does_not_hide_an_earlier_error(nested):
    class NoMatchBackend(ReorderingBackend):
        def geocode(self, inputs):
            return BatchGeocodingResult(results=[
                GeocodingResult(input_id=addr.input_id) for addr in inputs
            ])

    failing = ReorderingBackend(drop="1")
    first = CompositeBatchGeocoder([failing]) if nested else failing
    result = CompositeBatchGeocoder([first, NoMatchBackend()]).geocode(addresses(["a"]))

    assert result.results[0].input_id == "a"
    assert result.results[0].match_quality == "error"
    assert not result.results[0].matched
    assert result.errors


@pytest.mark.parametrize("entrypoint", ["census", "composite"])
def test_dropped_census_row_is_an_error_without_shifting_coordinates(monkeypatch, entrypoint):
    api = CensusAPIStub(drop="2")
    monkeypatch.setattr(census_geocoder, "_get_geocoder", lambda vintage: api)
    inputs = addresses(["a", "b", "c"])
    if entrypoint == "census":
        rows = census_geocoder.geocode_batch(inputs)
        assert rows[1].match_type == "Error"
    else:
        result = CompositeBatchGeocoder([CensusBatchGeocoder()]).geocode(inputs)
        rows = result.results
        assert rows[1].match_quality == "error"
        assert result.errors
    assert [row.lat for row in rows] == [1., None, 3.]
    assert not rows[1].matched


@pytest.mark.parametrize("corruption", ["duplicate", "unknown"])
def test_composite_rejects_ambiguous_response_ids(corruption):
    class InvalidBackend(ReorderingBackend):
        def geocode(self, inputs):
            result = super().geocode(inputs)
            if corruption == "duplicate":
                result.results.append(replace(result.results[0], lat=99.))
            else:
                result.results[0].input_id = "caller"
            return result

    result = CompositeBatchGeocoder([InvalidBackend()]).geocode(addresses(["caller"]))
    assert result.results[0].match_quality == "error"
    assert result.results[0].lat is None
    assert result.errors


@pytest.mark.parametrize("corruption", ["duplicate", "unknown"])
def test_census_rejects_ambiguous_response_ids(monkeypatch, corruption):
    class InvalidAPI(CensusAPIStub):
        def addressbatch(self, path, returntype):
            rows = super().addressbatch(path, returntype)
            if corruption == "duplicate":
                rows.append(dict(rows[0], lat=99.))
            else:
                rows[0]["id"] = "caller"
            return rows

    monkeypatch.setattr(census_geocoder, "_get_geocoder", lambda vintage: InvalidAPI())
    with pytest.raises(census_geocoder.CensusGeocodeError, match="unknown or duplicate"):
        census_geocoder.geocode_batch(addresses(["caller"]))


@pytest.mark.parametrize("chunk_size", [0, -1])
def test_invalid_chunk_size_is_rejected(chunk_size):
    with pytest.raises(ValueError, match="chunk_size"):
        CensusBatchGeocoder(chunk_size=chunk_size)
    with pytest.raises(ValueError, match="chunk_size"):
        census_geocoder.geocode_batch_chunked([], chunk_size=chunk_size)
