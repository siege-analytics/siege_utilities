"""Error-path tests for gazetteer modules.

Covers: base exceptions, WklsGazetteer, NominatimGazetteer,
CensusGazetteer, WikidataGazetteer — all error paths that can be
exercised WITHOUT network, GDAL, or geopandas.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.geo.gazetteers.base import (
    GazetteerAmbiguousError,
    GazetteerBackendError,
    GazetteerCandidate,
    GazetteerError,
    GazetteerNotFoundError,
    GazetteerResult,
)


# =========================================================================
# Base exception hierarchy
# =========================================================================

class TestErrorHierarchy:
    def test_not_found_is_gazetteer_error(self):
        assert issubclass(GazetteerNotFoundError, GazetteerError)

    def test_ambiguous_is_gazetteer_error(self):
        assert issubclass(GazetteerAmbiguousError, GazetteerError)

    def test_backend_is_gazetteer_error(self):
        assert issubclass(GazetteerBackendError, GazetteerError)

    def test_gazetteer_error_is_runtime_error(self):
        assert issubclass(GazetteerError, RuntimeError)


class TestGazetteerAmbiguousErrorCandidates:
    def test_carries_empty_candidates(self):
        err = GazetteerAmbiguousError("none", candidates=[])
        assert err.candidates == []

    def test_carries_multiple_candidates(self):
        c1 = GazetteerCandidate(name="A", canonical_path=("US",))
        c2 = GazetteerCandidate(name="B", canonical_path=("GB",))
        err = GazetteerAmbiguousError("two", candidates=[c1, c2])
        assert len(err.candidates) == 2
        assert err.candidates[0].name == "A"
        assert err.candidates[1].name == "B"

    def test_message_preserved(self):
        err = GazetteerAmbiguousError("custom msg", candidates=[])
        assert "custom msg" in str(err)


class TestGazetteerResultUnhashable:
    """GazetteerResult contains a mutable mapping and must not be hashable."""

    def test_raises_type_error_on_hash(self):
        r = GazetteerResult(
            name="X",
            canonical_path=("US",),
            geometry=None,
            centroid=None,
        )
        with pytest.raises(TypeError):
            hash(r)


# =========================================================================
# WklsGazetteer
# =========================================================================

from siege_utilities.geo.gazetteers import wkls_gazetteer as wg


class TestWklsUnavailableRaisesImportError:
    def test_missing_wkls_raises(self, monkeypatch):
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", False)
        with pytest.raises(ImportError, match="wkls"):
            wg.WklsGazetteer()


class TestWklsLookupEmptyName:
    def test_empty_string_raises(self, monkeypatch):
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
        monkeypatch.setattr(wg, "wkls", MagicMock())
        gz = wg.WklsGazetteer()
        with pytest.raises(ValueError, match="empty name"):
            gz.lookup("")

    def test_whitespace_only_raises(self, monkeypatch):
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
        monkeypatch.setattr(wg, "wkls", MagicMock())
        gz = wg.WklsGazetteer()
        with pytest.raises(ValueError, match="empty name"):
            gz.lookup("   ")


class TestWklsLookupInvalidISO3:
    def test_unknown_iso3_raises_value_error(self, monkeypatch):
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
        monkeypatch.setattr(wg, "wkls", MagicMock())
        gz = wg.WklsGazetteer()
        with pytest.raises(ValueError, match="unknown ISO-3"):
            gz.lookup("Birmingham", country_hint="XYZ")


class TestWklsSearchEmptyReturnsEmpty:
    def test_empty_search_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
        monkeypatch.setattr(wg, "wkls", MagicMock())
        gz = wg.WklsGazetteer()
        assert gz.search("") == []

    def test_whitespace_search_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
        monkeypatch.setattr(wg, "wkls", MagicMock())
        gz = wg.WklsGazetteer()
        assert gz.search("   ") == []


class TestWklsBackendError:
    def test_search_raises_backend_error_on_upstream_failure(self, monkeypatch):
        class _Broken:
            def __getattr__(self, name):
                raise RuntimeError("upstream exploded")
            def __getitem__(self, key):
                raise RuntimeError("upstream exploded")

        monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
        monkeypatch.setattr(wg, "wkls", _Broken())
        gz = wg.WklsGazetteer()
        with pytest.raises(GazetteerBackendError, match="search for"):
            gz.search("test_place")

    def test_lookup_not_found_raises(self, monkeypatch):
        """Lookup with no matches raises GazetteerNotFoundError."""
        pa = pytest.importorskip("pyarrow")

        empty_table = pa.table({
            "id": [], "country": [], "region": [],
            "subtype": [], "name_primary": [], "name_en": [],
        })

        class _EmptyChainable:
            def __getattr__(self, name):
                if name.startswith("_"):
                    raise AttributeError(name)
                return self
            def __getitem__(self, key):
                return self
            def to_arrow_table(self):
                return empty_table

        monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
        monkeypatch.setattr(wg, "wkls", _EmptyChainable())
        gz = wg.WklsGazetteer()
        with pytest.raises(GazetteerNotFoundError, match="no match"):
            gz.lookup("NonexistentPlace")


class TestWklsFetchGeometryErrors:
    def test_missing_shapely_raises_backend_error(self, monkeypatch):
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
        monkeypatch.setattr(wg, "wkls", MagicMock())
        gz = wg.WklsGazetteer()
        with patch.dict("sys.modules", {"shapely": None, "shapely.wkt": None}):
            # _fetch_geometry tries to import shapely.wkt
            with pytest.raises(GazetteerBackendError, match="shapely required"):
                gz._fetch_geometry("some-id")

    def test_resolve_failure_raises_backend_error(self, monkeypatch):
        pytest.importorskip("shapely.wkt")

        fake_wkls = MagicMock()
        fake_wkls.resolve.side_effect = RuntimeError("network down")
        monkeypatch.setattr(wg, "WKLS_AVAILABLE", True)
        monkeypatch.setattr(wg, "wkls", fake_wkls)
        gz = wg.WklsGazetteer()
        with pytest.raises(GazetteerBackendError, match="geometry fetch.*failed"):
            gz._fetch_geometry("bad-id")


# =========================================================================
# NominatimGazetteer
# =========================================================================

from siege_utilities.geo.gazetteers import nominatim_gazetteer as ng


class TestNominatimUnavailableRaisesImportError:
    def test_missing_geopy_raises(self, monkeypatch):
        monkeypatch.setattr(ng, "GEOPY_AVAILABLE", False)
        with pytest.raises(ImportError, match="geopy"):
            ng.NominatimGazetteer()


class TestNominatimLookupEmptyNameRaises:
    @pytest.mark.skipif(not ng.GEOPY_AVAILABLE, reason="geopy not installed")
    def test_empty_string_raises(self):
        gz = ng.NominatimGazetteer()
        with pytest.raises(ValueError, match="empty name"):
            gz.lookup("")

    @pytest.mark.skipif(not ng.GEOPY_AVAILABLE, reason="geopy not installed")
    def test_whitespace_raises(self):
        gz = ng.NominatimGazetteer()
        with pytest.raises(ValueError, match="empty name"):
            gz.lookup("   ")


class TestNominatimSearchEmptyReturnsEmpty:
    @pytest.mark.skipif(not ng.GEOPY_AVAILABLE, reason="geopy not installed")
    def test_empty_search_returns_empty(self):
        gz = ng.NominatimGazetteer()
        assert gz.search("") == []


class TestNominatimGeometryFromRowErrors:
    def test_missing_shapely_raises_backend_error(self):
        with patch.dict("sys.modules", {"shapely": None, "shapely.geometry": None}):
            with pytest.raises(GazetteerBackendError, match="shapely required"):
                ng._geometry_from_row({"geojson": None, "lat": 0, "lon": 0})


# =========================================================================
# CensusGazetteer
# =========================================================================

from siege_utilities.geo.gazetteers import census_gazetteer as cg


class TestCensusUnavailableRaisesImportError:
    def test_missing_requests_raises(self, monkeypatch):
        monkeypatch.setattr(cg, "REQUESTS_AVAILABLE", False)
        with pytest.raises(ImportError, match="requests"):
            cg.CensusGazetteer()

    def test_missing_shapely_raises(self, monkeypatch):
        monkeypatch.setattr(cg, "REQUESTS_AVAILABLE", True)
        monkeypatch.setattr(cg, "SHAPELY_AVAILABLE", False)
        with pytest.raises(ImportError, match="shapely"):
            cg.CensusGazetteer()


class TestCensusLookupEmptyNameRaises:
    @pytest.mark.skipif(
        not (cg.REQUESTS_AVAILABLE and cg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_empty_string_raises(self):
        gz = cg.CensusGazetteer()
        with pytest.raises(ValueError, match="empty name"):
            gz.lookup("")


class TestCensusLookupNonUSCountryRaises:
    @pytest.mark.skipif(
        not (cg.REQUESTS_AVAILABLE and cg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_non_us_country_raises_not_found(self):
        gz = cg.CensusGazetteer()
        with pytest.raises(GazetteerNotFoundError, match="US-only"):
            gz.lookup("Berlin", country_hint="DE")


class TestCensusSearchNegativeLimitRaises:
    @pytest.mark.skipif(
        not (cg.REQUESTS_AVAILABLE and cg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_negative_limit_raises_value_error(self):
        gz = cg.CensusGazetteer()
        with pytest.raises(ValueError, match="limit must be >= 0"):
            gz.search("test", limit=-1)


class TestCensusSearchNonUSReturnsEmpty:
    @pytest.mark.skipif(
        not (cg.REQUESTS_AVAILABLE and cg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_non_us_search_raises(self):
        # CensusGazetteer is US-only; a non-US country_hint is a usage error
        # that raises GazetteerNotFoundError rather than returning [] (SU-1).
        gz = cg.CensusGazetteer()
        with pytest.raises(GazetteerNotFoundError):
            gz.search("Berlin", country_hint="DE")


class TestCensusSearchEmptyReturnsEmpty:
    @pytest.mark.skipif(
        not (cg.REQUESTS_AVAILABLE and cg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_empty_search_returns_empty(self):
        gz = cg.CensusGazetteer()
        assert gz.search("") == []


# =========================================================================
# WikidataGazetteer
# =========================================================================

from siege_utilities.geo.gazetteers import wikidata_gazetteer as wdg


class TestWikidataUnavailableRaisesImportError:
    def test_missing_requests_raises(self, monkeypatch):
        monkeypatch.setattr(wdg, "REQUESTS_AVAILABLE", False)
        with pytest.raises(ImportError, match="requests"):
            wdg.WikidataGazetteer()

    def test_missing_shapely_raises(self, monkeypatch):
        monkeypatch.setattr(wdg, "REQUESTS_AVAILABLE", True)
        monkeypatch.setattr(wdg, "SHAPELY_AVAILABLE", False)
        with pytest.raises(ImportError, match="shapely"):
            wdg.WikidataGazetteer()


class TestWikidataLookupEmptyNameRaises:
    @pytest.mark.skipif(
        not (wdg.REQUESTS_AVAILABLE and wdg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_empty_string_raises(self):
        gz = wdg.WikidataGazetteer()
        with pytest.raises(ValueError, match="empty name"):
            gz.lookup("")


class TestWikidataSearchNegativeLimitRaises:
    @pytest.mark.skipif(
        not (wdg.REQUESTS_AVAILABLE and wdg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_negative_limit_raises(self):
        gz = wdg.WikidataGazetteer()
        with pytest.raises(ValueError, match="limit must be >= 0"):
            gz.search("test", limit=-1)


class TestWikidataSearchEmptyReturnsEmpty:
    @pytest.mark.skipif(
        not (wdg.REQUESTS_AVAILABLE and wdg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_empty_search_returns_empty(self):
        gz = wdg.WikidataGazetteer()
        assert gz.search("") == []


class TestWikidataSQLInjectionGuard:
    @pytest.mark.skipif(
        not (wdg.REQUESTS_AVAILABLE and wdg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_name_with_quotes_raises_value_error(self):
        gz = wdg.WikidataGazetteer()
        with pytest.raises(ValueError, match="illegal character"):
            gz.lookup('Birm"ingham')

    @pytest.mark.skipif(
        not (wdg.REQUESTS_AVAILABLE and wdg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_name_with_backslash_raises_value_error(self):
        gz = wdg.WikidataGazetteer()
        with pytest.raises(ValueError, match="illegal character"):
            gz.lookup("Birm\\ingham")

    @pytest.mark.skipif(
        not (wdg.REQUESTS_AVAILABLE and wdg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_country_with_quotes_raises_value_error(self):
        gz = wdg.WikidataGazetteer()
        with pytest.raises(ValueError, match="illegal character"):
            gz.lookup("Birmingham", country_hint='"US')


class TestWikidataOsmRelationIdValidation:
    @pytest.mark.skipif(
        not (wdg.REQUESTS_AVAILABLE and wdg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_non_numeric_osm_id_raises_backend_error(self):
        gz = wdg.WikidataGazetteer()
        with pytest.raises(GazetteerBackendError, match="not numeric"):
            gz._fetch_osm_relation_geometry("abc")

    @pytest.mark.skipif(
        not (wdg.REQUESTS_AVAILABLE and wdg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_negative_osm_id_raises_backend_error(self):
        gz = wdg.WikidataGazetteer()
        with pytest.raises(GazetteerBackendError, match="must be positive"):
            gz._fetch_osm_relation_geometry("-5")

    @pytest.mark.skipif(
        not (wdg.REQUESTS_AVAILABLE and wdg.SHAPELY_AVAILABLE),
        reason="requests or shapely not installed",
    )
    def test_zero_osm_id_raises_backend_error(self):
        gz = wdg.WikidataGazetteer()
        with pytest.raises(GazetteerBackendError, match="must be positive"):
            gz._fetch_osm_relation_geometry("0")


class TestWikidataParseWktPoint:
    def test_none_returns_none(self):
        assert wdg.WikidataGazetteer._parse_wkt_point(None) is None

    def test_empty_string_returns_none(self):
        assert wdg.WikidataGazetteer._parse_wkt_point("") is None

    def test_invalid_format_returns_none(self):
        assert wdg.WikidataGazetteer._parse_wkt_point("POLYGON(...)") is None

    def test_valid_point(self):
        result = wdg.WikidataGazetteer._parse_wkt_point("Point(-86.8 33.5)")
        assert result is not None
        assert abs(result[0] - (-86.8)) < 0.01
        assert abs(result[1] - 33.5) < 0.01


class TestWikidataStitchSegments:
    def test_empty_segments_returns_empty(self):
        assert wdg._stitch_segments_into_rings([]) == []

    def test_single_closed_ring_passes_through(self):
        ring = [(0, 0), (1, 0), (1, 1), (0, 0)]
        result = wdg._stitch_segments_into_rings([ring])
        assert len(result) == 1
        assert result[0] == ring

    def test_uncloseable_segment_dropped(self):
        # A segment that can't close to a ring is silently dropped.
        seg = [(0, 0), (1, 0), (2, 0)]
        result = wdg._stitch_segments_into_rings([seg])
        assert result == []


# =========================================================================
# Helper functions: _canonical_path_from_row, _admin_levels_from_row
# =========================================================================

from siege_utilities.geo.gazetteers.wkls_gazetteer import (
    _canonical_path_from_row,
    _admin_levels_from_row,
)


class TestCanonicalPathFromRow:
    def test_empty_row_returns_empty_tuple(self):
        assert _canonical_path_from_row({}) == ()

    def test_none_values_skipped(self):
        row = {"country": None, "region": None, "name_primary": None}
        assert _canonical_path_from_row(row) == ()

    def test_full_row(self):
        row = {"country": "US", "region": "AL", "name_primary": "Birmingham"}
        path = _canonical_path_from_row(row)
        assert path == ("US", "AL", "Birmingham")

    def test_region_same_as_country_skipped(self):
        row = {"country": "US", "region": "US", "name_primary": "Alabama"}
        path = _canonical_path_from_row(row)
        assert path == ("US", "Alabama")


class TestAdminLevelsFromRow:
    def test_empty_row_returns_empty_dict(self):
        assert _admin_levels_from_row({}) == {}

    def test_none_values_excluded(self):
        row = {"country": None, "region": None, "subtype": None}
        assert _admin_levels_from_row(row) == {}

    def test_full_row(self):
        row = {"country": "US", "region": "AL", "subtype": "locality"}
        result = _admin_levels_from_row(row)
        assert result == {"country": "US", "region": "AL", "subtype": "locality"}
