"""Nominatim geocoding classifier coverage."""

import pytest

from siege_utilities.geo.geocoding import NominatimGeoClassifier


def test_nominatim_geo_classifier_round_trips_json():
    classifier = NominatimGeoClassifier()
    classifier.place_rank_dict = {3: "City"}
    classifier.importance_dict = {0.6: "City"}

    restored = NominatimGeoClassifier().from_json(classifier.to_json())

    assert restored.get_place_ranks_by_label("City") == [3]
    assert restored.get_importance_threshold_by_label("City") == 0.6


def test_nominatim_geo_classifier_missing_tables_become_empty():
    restored = NominatimGeoClassifier().from_json("{}")

    assert restored.place_rank_dict == {}
    assert restored.importance_dict == {}
    assert restored.get_place_ranks_by_label("City") == []
    assert restored.get_importance_threshold_by_label("City") is None


def test_nominatim_geo_classifier_rejects_malformed_key_types():
    with pytest.raises(ValueError, match="lookup-table keys") as exc_info:
        NominatimGeoClassifier().from_json('{"place_ranks":{"bad":"City"}}')

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_nominatim_geo_classifier_rejects_non_object_payload():
    with pytest.raises(ValueError, match="decode to an object"):
        NominatimGeoClassifier().from_json("[]")


def test_nominatim_geo_classifier_rejects_non_object_tables():
    with pytest.raises(ValueError, match="place_ranks must be an object"):
        NominatimGeoClassifier().from_json('{"place_ranks": []}')
