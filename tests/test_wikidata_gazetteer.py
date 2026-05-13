"""Tests for the WikidataGazetteer backend.

Mocks both upstream services (Wikidata SPARQL + Overpass). The
backend is harder to test than Census because the SPARQL response
shape is verbose; tests focus on the translation logic and the
injection guard on `name`.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def wd_gaz():
    from siege_utilities.geo.gazetteers.wikidata_gazetteer import WikidataGazetteer
    return WikidataGazetteer()


def _sparql_response(bindings):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"results": {"bindings": bindings}}
    return resp


def _binding(name, *, osm_rel=None, coord=None, country=None):
    b: dict = {
        "item": {"value": f"http://www.wikidata.org/entity/Q{abs(hash(name)) % 100000}"},
        "itemLabel": {"value": name},
    }
    if osm_rel:
        b["osmRel"] = {"value": str(osm_rel)}
    if coord:
        b["coord"] = {"value": f"Point({coord[0]} {coord[1]})"}
    if country:
        b["countryLabel"] = {"value": country}
    return b


def _overpass_response_with_polygon():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {
        "elements": [{
            "type": "relation",
            "members": [{
                "type": "way",
                "role": "outer",
                "geometry": [
                    {"lon": 0.0, "lat": 0.0},
                    {"lon": 1.0, "lat": 0.0},
                    {"lon": 1.0, "lat": 1.0},
                    {"lon": 0.0, "lat": 1.0},
                    {"lon": 0.0, "lat": 0.0},
                ],
            }],
        }],
    }
    return resp


def test_lookup_empty_name_raises(wd_gaz):
    with pytest.raises(ValueError, match="empty name"):
        wd_gaz.lookup("")


def test_lookup_rejects_quote_in_name(wd_gaz):
    """SPARQL injection guard: the name lands inside a double-quoted
    SPARQL literal. Reject embedded quotes outright."""
    with pytest.raises(ValueError, match="illegal character"):
        wd_gaz.lookup('Foo" OR 1=1')


def test_lookup_rejects_backslash_in_name(wd_gaz):
    with pytest.raises(ValueError, match="illegal character"):
        wd_gaz.lookup("Foo\\bar")


def test_lookup_no_match_raises_not_found(wd_gaz):
    from siege_utilities.geo.gazetteers.base import GazetteerNotFoundError

    with patch.object(wd_gaz._session, "get", return_value=_sparql_response([])):
        with pytest.raises(GazetteerNotFoundError, match="no match"):
            wd_gaz.lookup("Nonexistentplace")


def test_lookup_multiple_matches_raises_ambiguous(wd_gaz):
    from siege_utilities.geo.gazetteers.base import GazetteerAmbiguousError

    bindings = [
        _binding("Springfield", country="United States"),
        _binding("Springfield", country="United Kingdom"),
    ]
    with patch.object(wd_gaz._session, "get", return_value=_sparql_response(bindings)):
        with pytest.raises(GazetteerAmbiguousError) as ei:
            wd_gaz.lookup("Springfield")
        assert len(ei.value.candidates) == 2


def test_lookup_single_match_with_osm_rel_fetches_polygon(wd_gaz):
    pytest.importorskip("shapely")
    from siege_utilities.geo.gazetteers.base import GazetteerResult

    bindings = [_binding("Appalachia", osm_rel=12345, country="United States")]
    sparql_resp = _sparql_response(bindings)
    overpass_resp = _overpass_response_with_polygon()

    def get_or_post(*args, **kwargs):
        if args and args[0] == wd_gaz._sparql_url:
            return sparql_resp
        raise AssertionError("unexpected GET")

    with patch.object(wd_gaz._session, "get", side_effect=get_or_post), \
         patch.object(wd_gaz._session, "post", return_value=overpass_resp):
        result = wd_gaz.lookup("Appalachia")

    assert isinstance(result, GazetteerResult)
    assert result.source == "wikidata"
    assert result.geometry.geom_type == "Polygon"


def test_lookup_falls_back_to_point_when_no_osm_rel(wd_gaz):
    pytest.importorskip("shapely")
    from siege_utilities.geo.gazetteers.base import GazetteerResult

    bindings = [_binding("Coordy", coord=(-122.5, 37.7), country="United States")]
    with patch.object(wd_gaz._session, "get", return_value=_sparql_response(bindings)):
        result = wd_gaz.lookup("Coordy")

    assert isinstance(result, GazetteerResult)
    assert result.geometry.geom_type == "Point"


def test_lookup_rejects_negative_osm_relation(wd_gaz):
    from siege_utilities.geo.gazetteers.base import GazetteerBackendError

    bindings = [_binding("X", osm_rel=-1, country="US")]
    with patch.object(wd_gaz._session, "get", return_value=_sparql_response(bindings)):
        with pytest.raises(GazetteerBackendError, match="positive"):
            wd_gaz.lookup("X")


def test_country_hint_filters_results(wd_gaz):
    """The country_hint substring-matches against the countryLabel
    field so callers can disambiguate."""
    bindings = [
        _binding("Springfield", country="United States"),
        _binding("Springfield", country="United Kingdom"),
    ]
    with patch.object(wd_gaz._session, "get", return_value=_sparql_response(bindings)):
        cands = wd_gaz.search("Springfield", country_hint="United States")
    assert len(cands) == 1
    assert cands[0].country == "United States"


def test_resolve_gazetteer_returns_wikidata_when_preferred():
    from siege_utilities.geo.gazetteers import resolve_gazetteer
    from siege_utilities.geo.gazetteers.wikidata_gazetteer import WikidataGazetteer

    gaz = resolve_gazetteer(prefer="wikidata")
    assert isinstance(gaz, WikidataGazetteer)
