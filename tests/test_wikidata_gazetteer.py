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


def test_country_hint_lands_in_sparql_query(wd_gaz):
    """The country_hint is pushed into the SPARQL WHERE clause as an
    ISO-code filter on the country entity, rather than being applied
    client-side after LIMIT. This prevents valid country-specific
    matches from being dropped outside the first page."""
    with patch.object(
        wd_gaz._session, "get", return_value=_sparql_response([]),
    ) as mock_get:
        wd_gaz.search("Springfield", country_hint="US")
    call_kwargs = mock_get.call_args.kwargs
    sent_query = call_kwargs["params"]["query"]
    assert "wdt:P297|wdt:P298" in sent_query, (
        f"country filter not in SPARQL query:\n{sent_query}"
    )
    assert '"US"' in sent_query


def test_country_hint_rejects_quote_injection(wd_gaz):
    """country_hint lands in a SPARQL literal so it gets the same
    injection guard as name."""
    with pytest.raises(ValueError, match="illegal character"):
        wd_gaz.search("Springfield", country_hint='US" OR 1=1')


def test_resolve_gazetteer_returns_wikidata_when_preferred():
    from siege_utilities.geo.gazetteers import resolve_gazetteer
    from siege_utilities.geo.gazetteers.wikidata_gazetteer import WikidataGazetteer

    gaz = resolve_gazetteer(prefer="wikidata")
    assert isinstance(gaz, WikidataGazetteer)


# ---------------------------------------------------------------------------
# Segment stitching: OSM relations split exterior across multiple ways
# ---------------------------------------------------------------------------

def test_stitch_segments_already_closed_passthrough():
    from siege_utilities.geo.gazetteers.wikidata_gazetteer import _stitch_segments_into_rings

    closed = [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]]
    rings = _stitch_segments_into_rings(closed)
    assert len(rings) == 1
    assert rings[0][0] == rings[0][-1]


def test_stitch_segments_two_open_segments_form_one_ring():
    """OSM relation with two outer ways that share endpoints and close
    when stitched in order."""
    from siege_utilities.geo.gazetteers.wikidata_gazetteer import _stitch_segments_into_rings

    seg1 = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
    seg2 = [(1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
    rings = _stitch_segments_into_rings([seg1, seg2])
    assert len(rings) == 1
    ring = rings[0]
    assert ring[0] == ring[-1] == (0.0, 0.0)
    assert (1.0, 1.0) in ring


def test_stitch_segments_reversed_segment():
    """Stitcher reverses a candidate segment whose endpoint matches the
    current ring's tail at the WRONG end."""
    from siege_utilities.geo.gazetteers.wikidata_gazetteer import _stitch_segments_into_rings

    seg1 = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
    # seg2 reversed -- starts at (0,0) but ought to be appended to (1,1).
    seg2_reversed = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    rings = _stitch_segments_into_rings([seg1, seg2_reversed])
    assert len(rings) == 1
    assert rings[0][0] == rings[0][-1]


def test_stitch_segments_two_independent_rings():
    """Two disjoint rings (e.g., multipolygon: mainland + island)."""
    from siege_utilities.geo.gazetteers.wikidata_gazetteer import _stitch_segments_into_rings

    mainland = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
    island = [(10.0, 10.0), (11.0, 10.0), (11.0, 11.0), (10.0, 11.0), (10.0, 10.0)]
    rings = _stitch_segments_into_rings([mainland, island])
    assert len(rings) == 2


def test_stitch_segments_drops_unclosable_segment():
    """A segment that cannot be closed is dropped, not raised. The
    higher-level call site decides how to react to 'no rings'."""
    from siege_utilities.geo.gazetteers.wikidata_gazetteer import _stitch_segments_into_rings

    lonely = [(0.0, 0.0), (1.0, 0.0)]  # no partner to close the ring
    rings = _stitch_segments_into_rings([lonely])
    assert rings == []


def _overpass_response_with_split_outer():
    """An OSM relation whose exterior is split across two outer ways."""
    resp = MagicMock(status_code=200)
    resp.json.return_value = {
        "elements": [{
            "type": "relation",
            "members": [
                {
                    "type": "way", "role": "outer",
                    "geometry": [
                        {"lon": 0.0, "lat": 0.0},
                        {"lon": 1.0, "lat": 0.0},
                        {"lon": 1.0, "lat": 1.0},
                    ],
                },
                {
                    "type": "way", "role": "outer",
                    "geometry": [
                        {"lon": 1.0, "lat": 1.0},
                        {"lon": 0.0, "lat": 1.0},
                        {"lon": 0.0, "lat": 0.0},
                    ],
                },
            ],
        }]
    }
    return resp


def test_fetch_osm_relation_geometry_stitches_split_outer(wd_gaz):
    """End-to-end: a split-outer OSM relation now produces a valid
    polygon instead of raising 'multipolygon assembly not implemented'."""
    from shapely.geometry import Polygon

    with patch.object(
        wd_gaz._session, "post", return_value=_overpass_response_with_split_outer(),
    ):
        geom = wd_gaz._fetch_osm_relation_geometry(123)
    assert isinstance(geom, Polygon)
    # The stitched ring is a unit square; area = 1.0.
    assert geom.area == pytest.approx(1.0)
