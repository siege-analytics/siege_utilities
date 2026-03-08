from __future__ import annotations

import pytest

from siege_utilities.geo.isochrones import (
    DEFAULT_ORS_BASE_URL,
    build_isochrone_request,
    get_isochrone,
)


class _DummyResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_build_isochrone_request_ors_defaults():
    req = build_isochrone_request(
        latitude=41.8781,
        longitude=-87.6298,
        travel_time_minutes=15,
    )

    assert req["provider"] == "openrouteservice"
    assert req["url"].startswith(f"{DEFAULT_ORS_BASE_URL}/v2/isochrones/")
    assert req["json"]["locations"] == [[-87.6298, 41.8781]]
    assert req["json"]["range"] == [900]


def test_build_isochrone_request_ors_custom_server_and_key():
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


def test_build_isochrone_request_valhalla_custom_server():
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


def test_get_isochrone_makes_expected_request(monkeypatch):
    captured = {}

    def _fake_post(url, headers, params, json, timeout):
        captured.update(
            {
                "url": url,
                "headers": headers,
                "params": params,
                "json": json,
                "timeout": timeout,
            }
        )
        return _DummyResponse({"type": "FeatureCollection", "features": []})

    monkeypatch.setattr("siege_utilities.geo.isochrones.requests.post", _fake_post)

    result = get_isochrone(
        latitude=34.0522,
        longitude=-118.2437,
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


def test_invalid_provider_raises():
    with pytest.raises(ValueError, match="provider must be one of"):
        build_isochrone_request(
            latitude=0,
            longitude=0,
            travel_time_minutes=5,
            provider="unknown",
        )


def test_invalid_travel_time_raises():
    with pytest.raises(ValueError, match="travel_time_minutes"):
        build_isochrone_request(
            latitude=0,
            longitude=0,
            travel_time_minutes=0,
        )
