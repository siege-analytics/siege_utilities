from __future__ import annotations

import pytest
import requests

from siege_utilities.geo.isochrones import (
    DEFAULT_ORS_BASE_URL,
    DEFAULT_VALHALLA_BASE_URL,
    IsochroneError,
    IsochroneNetworkError,
    IsochroneProvider,
    IsochroneProviderError,
    IsochroneRequest,
    OpenRouteServiceProvider,
    ValhallaProvider,
    build_isochrone_request,
    get_isochrone,
    get_provider,
    isochrone_to_geodataframe,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DummyResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, data, status_code: int = 200):
        self._data = data
        self.status_code = status_code
        self.text = str(data)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"{self.status_code}", response=self,
            )

    def json(self):
        return self._data


class _NonJsonResponse:
    """Response whose .json() raises ValueError."""

    status_code = 200
    text = "<html>Bad Gateway</html>"

    def raise_for_status(self):
        pass

    def json(self):
        raise ValueError("No JSON object could be decoded")


# ---------------------------------------------------------------------------
# build_isochrone_request
# ---------------------------------------------------------------------------


class TestBuildIsochroneRequest:
    def test_ors_defaults(self):
        req = build_isochrone_request(
            latitude=41.8781,
            longitude=-87.6298,
            travel_time_minutes=15,
        )
        assert req["provider"] == "openrouteservice"
        assert req["method"] == "POST"
        assert req["url"].startswith(f"{DEFAULT_ORS_BASE_URL}/v2/isochrones/")
        assert req["json"]["locations"] == [[-87.6298, 41.8781]]
        assert req["json"]["range"] == [900]

    def test_ors_custom_server_and_key(self):
        req = build_isochrone_request(
            latitude=41.8781,
            longitude=-87.6298,
            travel_time_minutes=10,
            provider="ors",
            base_url="https://ors.internal.local",
            api_key="abc123",
            profile="foot-walking",
        )
        assert req["url"] == "https://ors.internal.local/v2/isochrones/foot-walking"
        assert req["headers"]["Authorization"] == "abc123"

    def test_ors_extra_params_in_query(self):
        req = build_isochrone_request(
            latitude=0, longitude=0, travel_time_minutes=5,
            extra_params={"units": "mi"},
        )
        assert req["params"]["units"] == "mi"

    def test_valhalla_custom_server(self):
        req = build_isochrone_request(
            latitude=30.2672,
            longitude=-97.7431,
            travel_time_minutes=20,
            provider="valhalla",
            base_url="http://valhalla.svc.cluster.local:8002",
            profile="driving-car",
        )
        assert req["provider"] == "valhalla"
        assert req["url"] == "http://valhalla.svc.cluster.local:8002/isochrone"
        assert req["json"]["costing"] == "auto"
        assert req["json"]["contours"][0]["time"] == 20

    def test_valhalla_extra_params_merged(self):
        req = build_isochrone_request(
            latitude=0, longitude=0, travel_time_minutes=5,
            provider="valhalla",
            extra_params={"denoise": 0.5},
        )
        assert req["json"]["denoise"] == 0.5
        assert req["json"]["polygons"] is True  # original preserved

    def test_valhalla_profile_mapping(self):
        """All ORS profiles map to valid Valhalla costings."""
        cases = {
            "driving-car": "auto",
            "driving-hgv": "truck",
            "cycling-regular": "bicycle",
            "foot-walking": "pedestrian",
            "auto": "auto",
            "truck": "truck",
            "unknown-profile": "auto",  # default fallback
        }
        for ors_profile, expected_costing in cases.items():
            req = build_isochrone_request(
                latitude=0, longitude=0, travel_time_minutes=5,
                provider="valhalla", profile=ors_profile,
            )
            assert req["json"]["costing"] == expected_costing, (
                f"profile={ors_profile!r} → expected {expected_costing!r}"
            )

    def test_returns_isochrone_request_typed_dict(self):
        req = build_isochrone_request(
            latitude=0, longitude=0, travel_time_minutes=5,
        )
        assert isinstance(req, dict)
        assert set(IsochroneRequest.__annotations__) <= set(req.keys())


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="provider must be one of"):
            build_isochrone_request(
                latitude=0, longitude=0, travel_time_minutes=5,
                provider="unknown",
            )

    def test_invalid_travel_time_zero(self):
        with pytest.raises(ValueError, match="travel_time_minutes"):
            build_isochrone_request(
                latitude=0, longitude=0, travel_time_minutes=0,
            )

    def test_invalid_travel_time_negative(self):
        with pytest.raises(ValueError, match="travel_time_minutes"):
            build_isochrone_request(
                latitude=0, longitude=0, travel_time_minutes=-10,
            )

    def test_latitude_too_high(self):
        with pytest.raises(ValueError, match="latitude"):
            build_isochrone_request(
                latitude=91, longitude=0, travel_time_minutes=5,
            )

    def test_latitude_too_low(self):
        with pytest.raises(ValueError, match="latitude"):
            build_isochrone_request(
                latitude=-91, longitude=0, travel_time_minutes=5,
            )

    def test_longitude_too_high(self):
        with pytest.raises(ValueError, match="longitude"):
            build_isochrone_request(
                latitude=0, longitude=181, travel_time_minutes=5,
            )

    def test_longitude_too_low(self):
        with pytest.raises(ValueError, match="longitude"):
            build_isochrone_request(
                latitude=0, longitude=-181, travel_time_minutes=5,
            )

    def test_boundary_values_accepted(self):
        """Exact boundary values (-90/90, -180/180) are valid."""
        req = build_isochrone_request(
            latitude=90, longitude=-180, travel_time_minutes=1,
        )
        assert req["json"]["locations"] == [[-180.0, 90.0]]


# ---------------------------------------------------------------------------
# get_isochrone — happy path
# ---------------------------------------------------------------------------


class TestGetIsochrone:
    def test_makes_expected_post_request(self, monkeypatch):
        captured = {}

        def _fake_post(url, headers, params, json, timeout):
            captured.update(url=url, headers=headers, params=params,
                            json=json, timeout=timeout)
            return _DummyResponse({"type": "FeatureCollection", "features": []})

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _fake_post)

        result = get_isochrone(
            latitude=34.0522, longitude=-118.2437,
            travel_time_minutes=12,
            provider="openrouteservice",
            base_url="https://ors.internal",
            profile="cycling-regular",
            timeout_seconds=11,
        )

        assert result["type"] == "FeatureCollection"
        assert captured["url"] == "https://ors.internal/v2/isochrones/cycling-regular"
        assert captured["json"]["range"] == [720]
        assert captured["timeout"] == 11

    def test_max_retries_one_disables_retry(self, monkeypatch):
        call_count = 0

        def _fake_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.Timeout("timed out")

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _fake_post)

        with pytest.raises(IsochroneNetworkError, match="timed out"):
            get_isochrone(
                latitude=0, longitude=0, travel_time_minutes=5,
                max_retries=1,
            )
        assert call_count == 1


# ---------------------------------------------------------------------------
# get_isochrone — error paths
# ---------------------------------------------------------------------------


class TestGetIsochroneErrors:
    def test_timeout_raises_network_error(self, monkeypatch):
        def _timeout(*args, **kwargs):
            raise requests.exceptions.Timeout("connect timed out")

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _timeout)
        monkeypatch.setattr("siege_utilities.geo.isochrones.ISOCHRONE_RETRY_BACKOFF_BASE", 0)

        with pytest.raises(IsochroneNetworkError, match="timed out"):
            get_isochrone(
                latitude=0, longitude=0, travel_time_minutes=5,
                max_retries=1,
            )

    def test_connection_error_raises_network_error(self, monkeypatch):
        def _conn_err(*args, **kwargs):
            raise requests.exceptions.ConnectionError("refused")

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _conn_err)
        monkeypatch.setattr("siege_utilities.geo.isochrones.ISOCHRONE_RETRY_BACKOFF_BASE", 0)

        with pytest.raises(IsochroneNetworkError, match="refused"):
            get_isochrone(
                latitude=0, longitude=0, travel_time_minutes=5,
                max_retries=1,
            )

    def test_http_error_raises_provider_error(self, monkeypatch):
        def _fake_post(*args, **kwargs):
            return _DummyResponse({"error": "rate limited"}, status_code=403)

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _fake_post)

        with pytest.raises(IsochroneProviderError, match="403"):
            get_isochrone(
                latitude=0, longitude=0, travel_time_minutes=5,
                max_retries=1,
            )

    def test_non_json_response_raises_provider_error(self, monkeypatch):
        def _fake_post(*args, **kwargs):
            return _NonJsonResponse()

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _fake_post)

        with pytest.raises(IsochroneProviderError, match="non-JSON"):
            get_isochrone(
                latitude=0, longitude=0, travel_time_minutes=5,
                max_retries=1,
            )

    def test_non_dict_json_raises_provider_error(self, monkeypatch):
        def _fake_post(*args, **kwargs):
            return _DummyResponse([1, 2, 3])

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _fake_post)

        with pytest.raises(IsochroneProviderError, match="JSON object"):
            get_isochrone(
                latitude=0, longitude=0, travel_time_minutes=5,
                max_retries=1,
            )

    def test_exception_hierarchy(self):
        """Domain exceptions derive from IsochroneError."""
        assert issubclass(IsochroneNetworkError, IsochroneError)
        assert issubclass(IsochroneProviderError, IsochroneError)
        assert issubclass(IsochroneError, Exception)


# ---------------------------------------------------------------------------
# get_isochrone — retry behaviour
# ---------------------------------------------------------------------------


class TestGetIsochroneRetry:
    def test_retries_on_timeout(self, monkeypatch):
        call_count = 0

        def _flaky_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.Timeout("timed out")
            return _DummyResponse({"type": "FeatureCollection", "features": []})

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _flaky_post)
        monkeypatch.setattr("siege_utilities.geo.isochrones.ISOCHRONE_RETRY_BACKOFF_BASE", 0)

        result = get_isochrone(
            latitude=0, longitude=0, travel_time_minutes=5,
            max_retries=3,
        )
        assert result["type"] == "FeatureCollection"
        assert call_count == 3

    def test_retries_on_502(self, monkeypatch):
        call_count = 0

        def _flaky_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return _DummyResponse({"error": "bad gateway"}, status_code=502)
            return _DummyResponse({"type": "FeatureCollection", "features": []})

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _flaky_post)
        monkeypatch.setattr("siege_utilities.geo.isochrones.ISOCHRONE_RETRY_BACKOFF_BASE", 0)

        result = get_isochrone(
            latitude=0, longitude=0, travel_time_minutes=5,
            max_retries=3,
        )
        assert result["type"] == "FeatureCollection"
        assert call_count == 2

    def test_retries_on_429(self, monkeypatch):
        call_count = 0

        def _rate_limited(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return _DummyResponse({"error": "rate limited"}, status_code=429)
            return _DummyResponse({"type": "FeatureCollection", "features": []})

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _rate_limited)
        monkeypatch.setattr("siege_utilities.geo.isochrones.ISOCHRONE_RETRY_BACKOFF_BASE", 0)

        result = get_isochrone(
            latitude=0, longitude=0, travel_time_minutes=5,
            max_retries=3,
        )
        assert result["type"] == "FeatureCollection"
        assert call_count == 2

    def test_does_not_retry_on_403(self, monkeypatch):
        """Non-retryable HTTP errors fail immediately."""
        call_count = 0

        def _forbidden(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _DummyResponse({"error": "forbidden"}, status_code=403)

        monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _forbidden)

        with pytest.raises(IsochroneProviderError, match="403"):
            get_isochrone(
                latitude=0, longitude=0, travel_time_minutes=5,
                max_retries=3,
            )
        assert call_count == 1


# ---------------------------------------------------------------------------
# isochrone_to_geodataframe
# ---------------------------------------------------------------------------


class TestIsochroneToGeoDataFrame:
    def test_converts_geojson_features(self):
        """Convert a minimal GeoJSON FeatureCollection."""
        try:
            import geopandas  # noqa: F401
        except ImportError:
            pytest.skip("geopandas not available")

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
                        ],
                    },
                    "properties": {"value": 900},
                }
            ],
        }
        gdf = isochrone_to_geodataframe(geojson)
        assert len(gdf) == 1
        assert gdf.crs.to_epsg() == 4326
        assert "value" in gdf.columns

    def test_empty_features(self):
        """Empty features list produces empty GeoDataFrame."""
        try:
            import geopandas  # noqa: F401
        except ImportError:
            pytest.skip("geopandas not available")

        gdf = isochrone_to_geodataframe({"type": "FeatureCollection", "features": []})
        assert len(gdf) == 0

    def test_missing_features_key(self):
        """Missing 'features' key treated as empty."""
        try:
            import geopandas  # noqa: F401
        except ImportError:
            pytest.skip("geopandas not available")

        gdf = isochrone_to_geodataframe({"type": "FeatureCollection"})
        assert len(gdf) == 0

    def test_custom_crs_reprojection(self):
        """Passing a non-4326 CRS reprojects the result."""
        try:
            import geopandas  # noqa: F401
        except ImportError:
            pytest.skip("geopandas not available")

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[-87.6, 41.8], [-87.5, 41.8],
                             [-87.5, 41.9], [-87.6, 41.9], [-87.6, 41.8]]
                        ],
                    },
                    "properties": {"value": 900},
                }
            ],
        }
        gdf = isochrone_to_geodataframe(geojson, crs="EPSG:3857")
        assert gdf.crs.to_epsg() == 3857

    def test_default_crs_is_4326(self):
        """Default CRS is EPSG:4326 (no reprojection)."""
        try:
            import geopandas  # noqa: F401
        except ImportError:
            pytest.skip("geopandas not available")

        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
                        ],
                    },
                    "properties": {},
                }
            ],
        }
        gdf = isochrone_to_geodataframe(geojson)
        assert gdf.crs.to_epsg() == 4326


# ---------------------------------------------------------------------------
# JSON snapshot fixture — known ORS response
# ---------------------------------------------------------------------------

ORS_SNAPSHOT = {
    "type": "FeatureCollection",
    "bbox": [-87.6543, 41.8567, -87.6012, 41.8998],
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-87.6298, 41.8998],
                        [-87.6012, 41.8781],
                        [-87.6298, 41.8567],
                        [-87.6543, 41.8781],
                        [-87.6298, 41.8998],
                    ]
                ],
            },
            "properties": {
                "group_index": 0,
                "value": 900.0,
                "center": [-87.6298, 41.8781],
            },
        }
    ],
    "metadata": {
        "attribution": "openrouteservice.org | OpenStreetMap contributors",
        "service": "isochrones",
        "query": {
            "locations": [[-87.6298, 41.8781]],
            "range": [900],
            "profile": "driving-car",
        },
    },
}


class TestORSSnapshot:
    """Regression tests using a known ORS response snapshot."""

    def test_snapshot_parses_to_geodataframe(self):
        """Snapshot produces a one-row GeoDataFrame with expected columns."""
        try:
            import geopandas  # noqa: F401
        except ImportError:
            pytest.skip("geopandas not available")

        gdf = isochrone_to_geodataframe(ORS_SNAPSHOT)
        assert len(gdf) == 1
        assert gdf.crs.to_epsg() == 4326
        assert "geometry" in gdf.columns
        assert "value" in gdf.columns
        assert "group_index" in gdf.columns
        assert "center" in gdf.columns

    def test_snapshot_value_matches(self):
        """The ``value`` property (travel time in seconds) is preserved."""
        try:
            import geopandas  # noqa: F401
        except ImportError:
            pytest.skip("geopandas not available")

        gdf = isochrone_to_geodataframe(ORS_SNAPSHOT)
        assert gdf.iloc[0]["value"] == 900.0

    def test_snapshot_geometry_is_polygon(self):
        """The geometry is a valid Polygon."""
        try:
            import geopandas  # noqa: F401
            from shapely.geometry import Polygon
        except ImportError:
            pytest.skip("geopandas/shapely not available")

        gdf = isochrone_to_geodataframe(ORS_SNAPSHOT)
        geom = gdf.iloc[0].geometry
        assert isinstance(geom, Polygon)
        assert geom.is_valid


# ---------------------------------------------------------------------------
# Provider architecture
# ---------------------------------------------------------------------------


class TestIsochroneProviderABC:
    """Tests for the abstract base class itself."""

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            IsochroneProvider()  # type: ignore[abstract]

    def test_abc_defines_required_methods(self):
        abstract_methods = IsochroneProvider.__abstractmethods__
        assert "fetch" in abstract_methods
        assert "validate_config" in abstract_methods
        assert "provider_name" in abstract_methods


class TestOpenRouteServiceProvider:
    def test_instantiation_defaults(self):
        p = OpenRouteServiceProvider()
        assert p.provider_name == "openrouteservice"
        assert p.base_url == DEFAULT_ORS_BASE_URL
        assert p.api_key is None

    def test_instantiation_with_params(self):
        p = OpenRouteServiceProvider(
            api_key="test-key",
            base_url="https://ors.local",
            timeout_seconds=10,
            max_retries=1,
        )
        assert p.api_key == "test-key"
        assert p.base_url == "https://ors.local"
        assert p.timeout_seconds == 10
        assert p.max_retries == 1

    def test_validate_config_hosted_needs_key(self):
        """Hosted ORS (default URL) requires an API key."""
        assert not OpenRouteServiceProvider().validate_config()
        assert OpenRouteServiceProvider(api_key="k").validate_config()

    def test_validate_config_selfhosted_no_key_needed(self):
        """Self-hosted ORS does not require an API key."""
        p = OpenRouteServiceProvider(base_url="https://ors.internal")
        assert p.validate_config()

    def test_is_isochrone_provider(self):
        assert isinstance(OpenRouteServiceProvider(), IsochroneProvider)

    def test_fetch_delegates_to_get_isochrone(self, monkeypatch):
        """Fetch delegates to the function-based get_isochrone."""
        captured = {}

        def _fake_get_isochrone(**kwargs):
            captured.update(kwargs)
            return {"type": "FeatureCollection", "features": []}

        monkeypatch.setattr(
            "siege_utilities.geo.isochrones.get_isochrone", _fake_get_isochrone
        )
        p = OpenRouteServiceProvider(api_key="abc", base_url="https://ors.test")
        result = p.fetch(41.8781, -87.6298, 15, profile="foot-walking")

        assert result["type"] == "FeatureCollection"
        assert captured["latitude"] == 41.8781
        assert captured["longitude"] == -87.6298
        assert captured["travel_time_minutes"] == 15
        assert captured["provider"] == "openrouteservice"
        assert captured["api_key"] == "abc"
        assert captured["profile"] == "foot-walking"


class TestValhallaProvider:
    def test_instantiation_defaults(self):
        p = ValhallaProvider()
        assert p.provider_name == "valhalla"
        assert p.base_url == DEFAULT_VALHALLA_BASE_URL

    def test_instantiation_with_params(self):
        p = ValhallaProvider(
            base_url="http://valhalla.local:8002",
            timeout_seconds=15,
        )
        assert p.base_url == "http://valhalla.local:8002"
        assert p.timeout_seconds == 15

    def test_validate_config(self):
        assert ValhallaProvider().validate_config()
        assert ValhallaProvider(base_url="http://v.local").validate_config()

    def test_is_isochrone_provider(self):
        assert isinstance(ValhallaProvider(), IsochroneProvider)

    def test_fetch_delegates_to_get_isochrone(self, monkeypatch):
        captured = {}

        def _fake_get_isochrone(**kwargs):
            captured.update(kwargs)
            return {"type": "FeatureCollection", "features": []}

        monkeypatch.setattr(
            "siege_utilities.geo.isochrones.get_isochrone", _fake_get_isochrone
        )
        p = ValhallaProvider(base_url="http://v.test:8002")
        result = p.fetch(30.2672, -97.7431, 20)

        assert result["type"] == "FeatureCollection"
        assert captured["provider"] == "valhalla"
        assert captured["base_url"] == "http://v.test:8002"
        assert captured["travel_time_minutes"] == 20


class TestGetProviderFactory:
    def test_ors_shorthand(self):
        p = get_provider("ors", api_key="k")
        assert isinstance(p, OpenRouteServiceProvider)
        assert p.api_key == "k"

    def test_openrouteservice_full_name(self):
        p = get_provider("openrouteservice")
        assert isinstance(p, OpenRouteServiceProvider)

    def test_valhalla(self):
        p = get_provider("valhalla", base_url="http://v.local")
        assert isinstance(p, ValhallaProvider)
        assert p.base_url == "http://v.local"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="provider must be one of"):
            get_provider("mapbox")

    def test_kwargs_forwarded(self):
        p = get_provider("ors", api_key="key", timeout_seconds=5, max_retries=1)
        assert p.api_key == "key"
        assert p.timeout_seconds == 5
        assert p.max_retries == 1
