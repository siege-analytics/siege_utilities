"""Tests for the CensusGazetteer backend.

Mocks the two upstream HTTP services (Census Geocoder + TIGERWeb) so
the tests run without network. Mirrors the existing pattern in
test_nominatim_gazetteer.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def census_gaz():
    from siege_utilities.geo.gazetteers.census_gazetteer import CensusGazetteer
    return CensusGazetteer()


def _fake_geocoder_response(matches):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"result": {"addressMatches": matches}}
    return resp


def _fake_tigerweb_response(features):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"features": features}
    return resp


def _county_match(*, name="Jefferson", state="01", county="073"):
    return {
        "coordinates": {"x": -86.802, "y": 33.521},
        "geographies": {
            "Counties": [{
                "BASENAME": name,
                "STATE": state,
                "COUNTY": county,
                "GEOID": state + county,
            }],
        },
    }


def _tigerweb_feature(geoid):
    return {
        "type": "Feature",
        "properties": {"GEOID": geoid, "NAME": "Jefferson"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-87, 33], [-86, 33], [-86, 34], [-87, 34], [-87, 33]]],
        },
    }


def test_lookup_empty_name_raises(census_gaz):
    with pytest.raises(ValueError, match="empty name"):
        census_gaz.lookup("")


def test_lookup_non_us_country_hint_raises(census_gaz):
    from siege_utilities.geo.gazetteers.base import GazetteerNotFoundError

    with pytest.raises(GazetteerNotFoundError, match="US-only"):
        census_gaz.lookup("Toronto", country_hint="CA")


def test_lookup_no_match_raises_not_found(census_gaz):
    from siege_utilities.geo.gazetteers.base import GazetteerNotFoundError

    with patch.object(
        census_gaz._session, "get", return_value=_fake_geocoder_response([]),
    ):
        with pytest.raises(GazetteerNotFoundError, match="no match"):
            census_gaz.lookup("Notarealplace, ZZ")


def test_lookup_multiple_matches_raises_ambiguous(census_gaz):
    from siege_utilities.geo.gazetteers.base import GazetteerAmbiguousError

    matches = [
        _county_match(name="Jefferson", state="01", county="073"),
        _county_match(name="Jefferson", state="21", county="111"),
    ]
    with patch.object(
        census_gaz._session, "get", return_value=_fake_geocoder_response(matches),
    ):
        with pytest.raises(GazetteerAmbiguousError) as ei:
            census_gaz.lookup("Jefferson")
        assert len(ei.value.candidates) == 2


def test_lookup_single_match_fetches_polygon(census_gaz):
    pytest.importorskip("shapely")
    from siege_utilities.geo.gazetteers.base import GazetteerResult

    geocoder_resp = _fake_geocoder_response([
        _county_match(state="01", county="073"),
    ])
    tiger_resp = _fake_tigerweb_response([_tigerweb_feature("01073")])

    with patch.object(census_gaz._session, "get") as mock_get:
        # First call hits geocoder, second hits TIGERWeb.
        mock_get.side_effect = [geocoder_resp, tiger_resp]
        result = census_gaz.lookup("Birmingham, AL")

    assert isinstance(result, GazetteerResult)
    assert result.source == "census"
    assert result.country == "US"
    assert result.admin_levels["state_fips"] == "01"
    assert result.admin_levels["county_fips"] == "073"
    assert result.geometry.geom_type == "Polygon"


def test_lookup_backend_error_on_500(census_gaz):
    from siege_utilities.geo.gazetteers.base import GazetteerBackendError

    bad = MagicMock(status_code=500, text="upstream error")
    with patch.object(census_gaz._session, "get", return_value=bad):
        with pytest.raises(GazetteerBackendError, match="500"):
            census_gaz.lookup("Anywhere")


def test_resolve_gazetteer_returns_census_when_preferred():
    from siege_utilities.geo.gazetteers import resolve_gazetteer
    from siege_utilities.geo.gazetteers.census_gazetteer import CensusGazetteer

    gaz = resolve_gazetteer(prefer="census")
    assert isinstance(gaz, CensusGazetteer)
