"""NominatimGeoClassifier JSON contract tests."""

import pytest

from siege_utilities.geo.geocoding import NominatimGeoClassifier


def test_classifier_round_trips_json():
    classifier = NominatimGeoClassifier()
    loaded = NominatimGeoClassifier().from_json(classifier.to_json())
    assert loaded.place_rank_dict == classifier.place_rank_dict
    assert loaded.importance_dict == classifier.importance_dict


def test_classifier_ignores_unknown_top_level_keys_and_allows_missing_tables():
    classifier = NominatimGeoClassifier().from_json('{"unknown": true, "place_ranks": {"1": "State"}}')
    assert classifier.place_rank_dict == {1: "State"}
    assert classifier.importance_dict == {}


@pytest.mark.parametrize(
    "payload,match",
    [
        ("not-json", "JSON"),
        (None, "JSON"),
        (123, "JSON"),
        ("[]", "object"),
        ('{"place_ranks": []}', "place_ranks"),
        ('{"importance_thresholds": []}', "importance_thresholds"),
        ('{"place_ranks": {"bad": "City"}}', "place_ranks"),
        ('{"importance_thresholds": {"bad": "City"}}', "importance_thresholds"),
    ],
)
def test_classifier_rejects_malformed_payloads_transactionally(payload, match):
    classifier = NominatimGeoClassifier()
    original_place_ranks = classifier.place_rank_dict.copy()
    original_importance = classifier.importance_dict.copy()

    with pytest.raises(ValueError, match=match):
        classifier.from_json(payload)

    assert classifier.place_rank_dict == original_place_ranks
    assert classifier.importance_dict == original_importance
