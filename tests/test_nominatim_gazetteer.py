"""Tests for NominatimGazetteer (ELE-2483 PR-B).

geopy's Nominatim client is mocked — these tests cover the translation
layer between geopy ``Location`` objects and the
:class:`siege_utilities.geo.gazetteers.Gazetteer` protocol surface.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("geopy")
pytest.importorskip("shapely")


from siege_utilities.geo.gazetteers import (
    Gazetteer,
    GazetteerAmbiguousError,
    GazetteerBackendError,
    GazetteerNotFoundError,
    resolve_gazetteer,
)
from siege_utilities.geo.gazetteers import nominatim_gazetteer as ng


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _location(*, display, lat, lon, address, geojson=None, place_rank=10,
              osm_type="relation", osm_id=42, type_="city"):
    loc = MagicMock()
    loc.address = display
    loc.latitude = lat
    loc.longitude = lon
    loc.raw = {
        "display_name": display,
        "place_rank": place_rank,
        "address": address,
        "geojson": geojson,
        "osm_type": osm_type,
        "osm_id": osm_id,
        "type": type_,
    }
    return loc


@pytest.fixture
def fake_client(monkeypatch):
    """Replace NominatimGazetteer's geopy client with a controllable mock."""
    client = MagicMock()
    monkeypatch.setattr(ng.NominatimGazetteer, "_build_client",
                        lambda self: client)
    # Skip the rate-limit sleep so tests don't take 1s+ each.
    monkeypatch.setattr(ng, "_PUBLIC_RATE_LIMIT_S", 0.0)
    monkeypatch.setattr(ng, "_SELFHOSTED_RATE_LIMIT_S", 0.0)
    return client


# ---------------------------------------------------------------------------
# Construction & protocol conformance
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_provider_name(self, fake_client):
        gz = ng.NominatimGazetteer()
        assert gz.provider_name == "nominatim"
        assert isinstance(gz, Gazetteer)

    def test_self_hosted_uses_low_rate_limit(self, fake_client):
        gz = ng.NominatimGazetteer(server_url="http://nom.internal")
        # The instance picks the self-hosted constant at construction.
        assert gz._rate_limit == ng._SELFHOSTED_RATE_LIMIT_S

    def test_unavailable_raises(self, monkeypatch):
        monkeypatch.setattr(ng, "GEOPY_AVAILABLE", False)
        with pytest.raises(ImportError, match="geopy"):
            ng.NominatimGazetteer()


# ---------------------------------------------------------------------------
# lookup
# ---------------------------------------------------------------------------

class TestLookup:
    def test_basic_lookup_with_polygon(self, fake_client):
        fake_client.geocode.return_value = [
            _location(
                display="Birmingham, Jefferson County, Alabama, USA",
                lat=33.5, lon=-86.8,
                address={"city": "Birmingham", "county": "Jefferson County",
                         "state": "Alabama", "country": "United States",
                         "country_code": "us"},
                geojson={"type": "Polygon",
                         "coordinates": [[[-86.9, 33.4], [-86.7, 33.4],
                                          [-86.7, 33.6], [-86.9, 33.6],
                                          [-86.9, 33.4]]]},
                type_="city",
            )
        ]
        gz = ng.NominatimGazetteer()
        r = gz.lookup("Birmingham", country_hint="US")
        assert r.name == "Birmingham"
        assert r.country == "US"
        assert "US" in r.canonical_path
        assert r.geometry.geom_type == "Polygon"
        assert r.source == "nominatim"

    def test_falls_back_to_point_when_no_geojson(self, fake_client):
        fake_client.geocode.return_value = [
            _location(
                display="Lausanne, Switzerland",
                lat=46.5, lon=6.6,
                address={"city": "Lausanne", "country_code": "ch"},
                geojson=None, type_="city",
            )
        ]
        gz = ng.NominatimGazetteer()
        r = gz.lookup("Lausanne", country_hint="CH")
        assert r.geometry.geom_type == "Point"
        assert r.country == "CH"

    def test_ambiguous_raises_with_candidates(self, fake_client):
        fake_client.geocode.return_value = [
            _location(display="Birmingham, AL", lat=33.5, lon=-86.8,
                      address={"city": "Birmingham", "country_code": "us"}),
            _location(display="Birmingham, UK", lat=52.5, lon=-1.9,
                      address={"city": "Birmingham", "country_code": "gb"}),
        ]
        gz = ng.NominatimGazetteer()
        with pytest.raises(GazetteerAmbiguousError) as exc_info:
            gz.lookup("Birmingham")
        assert len(exc_info.value.candidates) == 2

    def test_ambiguous_after_hints_still_raises(self, fake_client):
        """Hints narrow but don't promise uniqueness."""
        fake_client.geocode.return_value = [
            _location(display="Birmingham, AL", lat=33.5, lon=-86.8,
                      address={"city": "Birmingham", "state": "Alabama",
                               "country_code": "us"}),
            _location(display="Birmingham, MI", lat=42.5, lon=-83.2,
                      address={"city": "Birmingham", "state": "Michigan",
                               "country_code": "us"}),
        ]
        gz = ng.NominatimGazetteer()
        with pytest.raises(GazetteerAmbiguousError) as exc_info:
            gz.lookup("Birmingham", country_hint="US")
        assert "country_hint='US'" in str(exc_info.value)

    def test_unknown_raises_not_found(self, fake_client):
        fake_client.geocode.return_value = []
        gz = ng.NominatimGazetteer()
        with pytest.raises(GazetteerNotFoundError):
            gz.lookup("Atlantis")

    def test_empty_name_raises(self, fake_client):
        gz = ng.NominatimGazetteer()
        with pytest.raises(ValueError, match="empty"):
            gz.lookup("")

    def test_geocoder_failure_translated(self, fake_client):
        from geopy.exc import GeocoderServiceError
        fake_client.geocode.side_effect = GeocoderServiceError("upstream 500")
        gz = ng.NominatimGazetteer()
        with pytest.raises(GazetteerBackendError, match="failed"):
            gz.lookup("Birmingham")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_returns_candidates(self, fake_client):
        fake_client.geocode.return_value = [
            _location(display="Birmingham, AL", lat=33.5, lon=-86.8,
                      address={"city": "Birmingham", "country_code": "us"}),
            _location(display="Birmingham, UK", lat=52.5, lon=-1.9,
                      address={"city": "Birmingham", "country_code": "gb"}),
        ]
        gz = ng.NominatimGazetteer()
        cands = gz.search("Birmingham")
        assert {c.country for c in cands} == {"US", "GB"}

    def test_search_empty_returns_empty(self, fake_client):
        gz = ng.NominatimGazetteer()
        assert gz.search("") == []


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

class TestCache:
    def test_lookup_cached(self, fake_client):
        fake_client.geocode.return_value = [
            _location(display="Birmingham, AL", lat=33.5, lon=-86.8,
                      address={"city": "Birmingham", "country_code": "us"})
        ]
        gz = ng.NominatimGazetteer(cache_size=4)
        gz.lookup("Birmingham", country_hint="US")
        gz.lookup("Birmingham", country_hint="US")
        assert fake_client.geocode.call_count == 1


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestFactory:
    def test_prefer_nominatim(self, fake_client):
        gz = resolve_gazetteer(prefer="nominatim")
        assert gz.provider_name == "nominatim"
