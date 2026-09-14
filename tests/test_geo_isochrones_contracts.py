import httpx
import pytest

from siege_utilities import build_isochrone_request
from siege_utilities import get_isochrone
from siege_utilities import isochrone_to_geodataframe
from siege_utilities.geo.isochrones import IsochroneNetworkError, IsochroneProviderError


def test_build_isochrone_request_openrouteservice_shape():
    req = build_isochrone_request(
        38.9,
        -77.0,
        15,
        provider="ors",
        base_url="https://ors.example.test/",
        profile="foot-walking",
        api_key="secret-token",
        extra_params={"attributes": ["area"]},
    )

    assert req["provider"] == "openrouteservice"
    assert req["method"] == "POST"
    assert req["url"] == "https://ors.example.test/v2/isochrones/foot-walking"
    assert req["headers"]["Authorization"] == "secret-token"
    assert req["params"] == {"attributes": ["area"]}
    assert req["json"] == {"locations": [[-77.0, 38.9]], "range": [900]}


def test_build_isochrone_request_valhalla_shape_and_costing():
    req = build_isochrone_request(
        38.9,
        -77.0,
        12,
        provider="valhalla",
        base_url="http://valhalla.example.test/",
        profile="foot-walking",
        extra_params={"denoise": 0.5},
    )

    assert req["provider"] == "valhalla"
    assert req["method"] == "POST"
    assert req["url"] == "http://valhalla.example.test/isochrone"
    assert req["params"] == {}
    assert req["json"]["locations"] == [{"lat": 38.9, "lon": -77.0}]
    assert req["json"]["costing"] == "pedestrian"
    assert req["json"]["contours"] == [{"time": 12}]
    assert req["json"]["polygons"] is True
    assert req["json"]["denoise"] == 0.5


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"latitude": 91, "longitude": 0, "travel_time_minutes": 10}, "latitude"),
        ({"latitude": 0, "longitude": 181, "travel_time_minutes": 10}, "longitude"),
        ({"latitude": 0, "longitude": 0, "travel_time_minutes": 0}, "travel_time_minutes"),
        ({"latitude": 0, "longitude": 0, "travel_time_minutes": 10, "provider": "bad"}, "provider"),
    ],
)
def test_build_isochrone_request_validates_inputs(kwargs, match):
    with pytest.raises(ValueError, match=match):
        build_isochrone_request(**kwargs)


def test_get_isochrone_returns_json_after_retryable_response(monkeypatch):
    calls = []

    class FakeResponse:
        text = '{"type":"FeatureCollection"}'

        def __init__(self, status_code):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "bad",
                    request=httpx.Request("POST", "http://x"),
                    response=httpx.Response(self.status_code),
                )

        def json(self):
            return {"type": "FeatureCollection", "features": []}

    def fake_dispatch(request_def, timeout_seconds):
        calls.append((request_def, timeout_seconds))
        return FakeResponse(503 if len(calls) == 1 else 200)

    monkeypatch.setattr("siege_utilities.geo.isochrones._dispatch_request", fake_dispatch)
    monkeypatch.setattr("siege_utilities.geo.isochrones.time.sleep", lambda _seconds: None)

    data = get_isochrone(
        38.9, -77.0, 5, provider="valhalla", max_retries=2, timeout_seconds=7
    )

    assert data == {"type": "FeatureCollection", "features": []}
    assert len(calls) == 2
    assert all(timeout == 7 for _, timeout in calls)


def test_get_isochrone_wraps_timeout_after_retries(monkeypatch):
    attempts = []

    def fake_dispatch(request_def, timeout_seconds):
        attempts.append(timeout_seconds)
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr("siege_utilities.geo.isochrones._dispatch_request", fake_dispatch)
    monkeypatch.setattr("siege_utilities.geo.isochrones.time.sleep", lambda _seconds: None)

    with pytest.raises(IsochroneNetworkError, match="timed out"):
        get_isochrone(38.9, -77.0, 5, max_retries=2, timeout_seconds=3)

    assert attempts == [3, 3]


def test_get_isochrone_rejects_non_object_json(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = "[]"

        def raise_for_status(self):
            return None

        def json(self):
            return []

    monkeypatch.setattr(
        "siege_utilities.geo.isochrones._dispatch_request",
        lambda request_def, timeout_seconds: FakeResponse(),
    )

    with pytest.raises(IsochroneProviderError, match="JSON object"):
        get_isochrone(38.9, -77.0, 5)


def test_isochrone_to_geodataframe_empty_feature_collection():
    gdf = isochrone_to_geodataframe({"type": "FeatureCollection", "features": []})

    assert gdf.empty
