"""Tests for siege_utilities.geo.gazetteers (ELE-2483 PR-A).

The WKLS upstream is mocked (network-bound, returns sedonadb rows). We
test the translation layer — protocol conformance, exception
discipline, search → candidate translation, lookup → result
translation, the LRU cache, and ISO-3 → ISO-2 country code mapping.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.geo.gazetteers import (
    Gazetteer,
    GazetteerAmbiguousError,
    GazetteerBackendError,
    GazetteerCandidate,
    GazetteerError,
    GazetteerNotFoundError,
    GazetteerResult,
    resolve_gazetteer,
)
from siege_utilities.geo.gazetteers import wkls_gazetteer as wg


# ---------------------------------------------------------------------------
# Helpers: build a fake upstream wkls module
# ---------------------------------------------------------------------------

def _arrow_table_from_rows(rows: list[dict]):
    """Build a real pyarrow.Table from row dicts so the WklsGazetteer's
    arrow-iteration code path is exercised end-to-end."""
    pa = pytest.importorskip("pyarrow")
    if not rows:
        return pa.table({"id": [], "country": [], "region": [],
                         "subtype": [], "name_primary": [], "name_en": []})
    cols = {k: [r.get(k) for r in rows] for k in
            ("id", "country", "region", "subtype", "name_primary", "name_en")}
    return pa.table(cols)


class _FakeChainable:
    """Mimics wkls.core.ChainableDataFrame for both attribute and dict access."""

    def __init__(self, rows: list[dict], geometries: dict[str, str] | None = None):
        self._rows = rows
        self._geometries = geometries or {}

    def __getattr__(self, name):
        # Drill into rows whose region/country matches a chained code.
        if name.startswith("_"):
            raise AttributeError(name)
        filtered = [
            r for r in self._rows
            if name.lower() in str(r.get("country", "")).lower()
            or name.lower() in str(r.get("region", "")).lower()
        ]
        return _FakeChainable(filtered or self._rows, self._geometries)

    def __getitem__(self, key):
        if isinstance(key, str) and key.startswith("%") and key.endswith("%"):
            needle = key.strip("%").lower()
            filtered = [
                r for r in self._rows
                if needle in str(r.get("name_primary", "")).lower()
                or needle in str(r.get("name_en", "")).lower()
                or needle in str(r.get("region", "")).lower()
                or needle in str(r.get("country", "")).lower()
            ]
            return _FakeChainable(filtered, self._geometries)
        raise TypeError(f"FakeChainable[{key!r}] not supported")

    def to_arrow_table(self):
        return _arrow_table_from_rows(self._rows)


def _make_resolve(geometries: dict[str, str]):
    """Build a wkls.resolve(id) → object-with-.wkt() callable."""
    def resolve(place_id: str):
        wkt_str = geometries.get(place_id)
        if not wkt_str:
            raise KeyError(place_id)
        node = MagicMock()
        node.wkt = MagicMock(return_value=wkt_str)
        return node
    return resolve


# ---------------------------------------------------------------------------
# Protocol structure
# ---------------------------------------------------------------------------

class TestProtocol:
    def test_result_is_unhashable(self):
        # Mutable metadata mapping → must not be hashable.
        from shapely.geometry import Point
        r = GazetteerResult(
            name="X", canonical_path=("US", "AL"),
            geometry=Point(0, 0), centroid=Point(0, 0),
        )
        with pytest.raises(TypeError):
            hash(r)

    def test_candidate_round_trip(self):
        c = GazetteerCandidate(
            name="Birmingham", canonical_path=("US", "AL", "Birmingham"),
            country="US", source="wkls",
        )
        assert c.country == "US"
        assert c.source == "wkls"

    def test_ambiguous_carries_candidates(self):
        c1 = GazetteerCandidate(
            name="Birmingham", canonical_path=("US", "AL"), country="US",
        )
        c2 = GazetteerCandidate(
            name="Birmingham", canonical_path=("GB",), country="GB",
        )
        err = GazetteerAmbiguousError("two matches", [c1, c2])
        assert len(err.candidates) == 2
        assert err.candidates[0].country == "US"

    def test_error_hierarchy(self):
        assert issubclass(GazetteerNotFoundError, GazetteerError)
        assert issubclass(GazetteerAmbiguousError, GazetteerError)
        assert issubclass(GazetteerBackendError, GazetteerError)


# ---------------------------------------------------------------------------
# WklsGazetteer
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_wkls(monkeypatch):
    """Replace the wkls module-attribute on wg with a controllable fake."""
    rows = [
        {"id": "uuid-bham-al", "country": "US", "region": "US-AL",
         "subtype": "locality", "name_primary": "Birmingham", "name_en": "Birmingham"},
        {"id": "uuid-bham-uk", "country": "GB", "region": "GB-WMD",
         "subtype": "locality", "name_primary": "Birmingham", "name_en": "Birmingham"},
        {"id": "uuid-alabama", "country": "US", "region": "US-AL",
         "subtype": "region", "name_primary": "Alabama", "name_en": "Alabama"},
    ]
    geometries = {
        "uuid-bham-al": "POLYGON((-86.9 33.4, -86.7 33.4, -86.7 33.6, -86.9 33.6, -86.9 33.4))",
        "uuid-bham-uk": "POLYGON((-2.0 52.4, -1.8 52.4, -1.8 52.5, -2.0 52.5, -2.0 52.4))",
        "uuid-alabama": "POLYGON((-88.5 30.2, -84.9 30.2, -84.9 35.0, -88.5 35.0, -88.5 30.2))",
    }
    fake = _FakeChainable(rows, geometries)
    fake.resolve = _make_resolve(geometries)
    monkeypatch.setattr(wg, "wkls", fake)
    monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
    return fake


class TestWklsGazetteerConstruction:
    def test_unavailable_raises(self, monkeypatch):
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", False)
        with pytest.raises(ImportError, match="wkls"):
            wg.WklsGazetteer()

    def test_provider_name(self, fake_wkls):
        gz = wg.WklsGazetteer()
        assert gz.provider_name == "wkls"
        assert isinstance(gz, Gazetteer)


class TestWklsGazetteerLookup:
    def test_basic_lookup_with_country_hint(self, fake_wkls):
        gz = wg.WklsGazetteer()
        result = gz.lookup("Birmingham", country_hint="US")
        assert result.name == "Birmingham"
        assert result.country == "US"
        assert "US" in result.canonical_path
        assert result.source == "wkls"
        assert result.geometry is not None
        assert result.centroid is not None

    def test_lookup_ambiguous_raises_with_candidates(self, fake_wkls):
        gz = wg.WklsGazetteer()
        with pytest.raises(GazetteerAmbiguousError) as exc_info:
            gz.lookup("Birmingham")  # no country_hint → ambiguous
        assert len(exc_info.value.candidates) == 2

    def test_lookup_ambiguous_after_hints_still_raises(self, fake_wkls, monkeypatch):
        """Ambiguity after hints must still surface — hints narrow, they
        don't promise uniqueness."""
        # Two US Birminghams (both legitimately exist in real data).
        rows = [
            {"id": "uuid-bham-al", "country": "US", "region": "US-AL",
             "subtype": "locality", "name_primary": "Birmingham",
             "name_en": "Birmingham"},
            {"id": "uuid-bham-mi", "country": "US", "region": "US-MI",
             "subtype": "locality", "name_primary": "Birmingham",
             "name_en": "Birmingham"},
        ]
        fake = _FakeChainable(rows, {})
        monkeypatch.setattr(wg, "wkls", fake)
        gz = wg.WklsGazetteer()
        with pytest.raises(GazetteerAmbiguousError) as exc_info:
            gz.lookup("Birmingham", country_hint="US")
        assert "country_hint='US'" in str(exc_info.value)
        assert len(exc_info.value.candidates) == 2

    def test_lookup_unknown_iso3_raises_value_error(self, fake_wkls):
        """Unknown ISO-3 should be rejected as a caller error, not
        translated to a backend error."""
        gz = wg.WklsGazetteer()
        with pytest.raises(ValueError, match="unknown ISO-3"):
            gz.lookup("Birmingham", country_hint="XYZ")

    def test_lookup_unknown_raises_not_found(self, fake_wkls):
        gz = wg.WklsGazetteer()
        with pytest.raises(GazetteerNotFoundError):
            gz.lookup("Atlantis", country_hint="US")

    def test_lookup_empty_name_raises(self, fake_wkls):
        gz = wg.WklsGazetteer()
        with pytest.raises(ValueError, match="empty"):
            gz.lookup("")

    def test_iso3_country_hint_translated(self, fake_wkls):
        """USA → US; the chain access works on the 2-letter form."""
        gz = wg.WklsGazetteer()
        result = gz.lookup("Birmingham", country_hint="USA")
        assert result.country == "US"


class TestWklsGazetteerSearch:
    def test_search_returns_candidates(self, fake_wkls):
        gz = wg.WklsGazetteer()
        candidates = gz.search("Birmingham")
        names = [c.name for c in candidates]
        assert "Birmingham" in names

    def test_search_respects_country_hint(self, fake_wkls):
        gz = wg.WklsGazetteer()
        candidates = gz.search("Birmingham", country_hint="US")
        countries = [c.country for c in candidates]
        # Only US match should be in the filtered set.
        assert all(c == "US" for c in countries)

    def test_search_empty_name_returns_empty(self, fake_wkls):
        gz = wg.WklsGazetteer()
        assert gz.search("") == []

    def test_search_limit(self, fake_wkls):
        gz = wg.WklsGazetteer()
        # The fixture has 3 rows; limit=1 should return at most 1.
        candidates = gz.search("A", limit=1)
        assert len(candidates) <= 1


class TestWklsGazetteerCache:
    def test_geometry_lookup_cached(self, fake_wkls):
        gz = wg.WklsGazetteer(cache_size=8)
        # Use the unambiguous fixture row directly via the internal API.
        # First call hits resolve(); second should be cached.
        with patch.object(fake_wkls, "resolve", wraps=fake_wkls.resolve) as spy:
            r1 = gz.lookup("Birmingham", country_hint="US")
            r2 = gz.lookup("Birmingham", country_hint="US")
            # geometry result is identical; resolve called only once.
            assert r1.geometry == r2.geometry
            assert spy.call_count == 1


class TestWklsGazetteerBackendErrors:
    def test_search_translates_upstream_failure(self, fake_wkls, monkeypatch):
        """Upstream raising during search → translated to GazetteerBackendError."""
        class _Broken:
            def __getattr__(self, name):
                raise RuntimeError("backend kaboom")
            def __getitem__(self, key):
                raise RuntimeError("backend kaboom")
        monkeypatch.setattr(wg, "wkls", _Broken())
        gz = wg.WklsGazetteer()
        with pytest.raises(GazetteerBackendError, match="search for"):
            gz.search("X")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestResolveGazetteer:
    def test_prefer_wkls(self, fake_wkls):
        gz = resolve_gazetteer(prefer="wkls")
        assert gz.provider_name == "wkls"

    def test_prefer_unimplemented_backends_raise(self, fake_wkls):
        for name in ("nominatim", "census", "wikidata"):
            with pytest.raises(NotImplementedError):
                resolve_gazetteer(prefer=name)

    def test_prefer_invalid_raises(self, fake_wkls):
        with pytest.raises(ValueError, match="prefer must be"):
            resolve_gazetteer(prefer="atlas")

    def test_auto_select_wkls_when_available(self, fake_wkls):
        gz = resolve_gazetteer()
        assert gz.provider_name == "wkls"

    def test_auto_select_no_backend_raises(self, monkeypatch):
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", False)
        with pytest.raises(RuntimeError, match="No gazetteer backend"):
            resolve_gazetteer()
