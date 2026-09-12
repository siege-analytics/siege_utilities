"""Property tests: CRS transformation round-trip invariants.

For any valid (lat, lon) in WGS84, the transformation

    WGS84 → target_CRS → WGS84

must return coordinates within numerical tolerance of the input.

This closes the CRS-round-trip half of the modernization memo (#1190)
item #5: hypothesis property tests on geo/. The memo explicitly named
CRS transforms as a textbook property-test target.

Round-trip identity is a canonical property-test shape: for all valid
inputs, the composition of a transform with its inverse is the
identity within tolerance. If pyproj / any CRS-transform library
regresses, this test catches it deterministically across many random
inputs.

Coverage:
  1. WGS84 (EPSG:4326) → Web Mercator (EPSG:3857) → WGS84
  2. WGS84 → US National Atlas Equal Area (EPSG:2163) → WGS84
  3. WGS84 → NAD83 (EPSG:4269) → WGS84

Excludes polar regions (|lat| > 85) because Web Mercator distorts
extremely near the poles and round-trip precision degrades.
"""

from __future__ import annotations

import pytest

pyproj = pytest.importorskip("pyproj")
hypothesis = pytest.importorskip("hypothesis")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


# Lat/lon strategies. Web Mercator degrades near poles; clip to ±85.
_LAT = st.floats(
    min_value=-85.0,
    max_value=85.0,
    allow_nan=False,
    allow_infinity=False,
)
_LON = st.floats(
    min_value=-180.0,
    max_value=180.0,
    allow_nan=False,
    allow_infinity=False,
)

# Tolerance for round-trip precision. Web Mercator round-trips to
# ~1e-9 degrees for mid-latitudes; equal-area projections are similar.
# 1e-6 degrees ≈ 0.1 meters at the equator — plenty of headroom for
# real-world use while still catching implementation regressions.
_TOLERANCE_DEG = 1e-6


@given(lat=_LAT, lon=_LON)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,  # pyproj first-call is slow due to PROJ data caching
)
def test_web_mercator_roundtrip_identity(lat: float, lon: float) -> None:
    """WGS84 → EPSG:3857 → WGS84 returns input within tolerance."""
    to_mercator = pyproj.Transformer.from_crs(4326, 3857, always_xy=True)
    from_mercator = pyproj.Transformer.from_crs(3857, 4326, always_xy=True)

    x, y = to_mercator.transform(lon, lat)
    lon_back, lat_back = from_mercator.transform(x, y)

    assert abs(lat - lat_back) < _TOLERANCE_DEG, (
        f"lat drift: {lat} → {lat_back} (delta {abs(lat - lat_back):.2e})"
    )
    assert abs(lon - lon_back) < _TOLERANCE_DEG, (
        f"lon drift: {lon} → {lon_back} (delta {abs(lon - lon_back):.2e})"
    )


@given(lat=_LAT, lon=_LON)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_us_national_atlas_equal_area_roundtrip_identity(
    lat: float, lon: float,
) -> None:
    """WGS84 → EPSG:2163 (US National Atlas Equal Area) → WGS84.

    2163 is the library's default `PROJECTION_CRS` (see conf/defaults.py);
    a round-trip regression here would break every reprojection call in
    the reporting + analytics stacks. The equal-area projection is
    US-centric but the round-trip identity holds globally.
    """
    to_2163 = pyproj.Transformer.from_crs(4326, 2163, always_xy=True)
    from_2163 = pyproj.Transformer.from_crs(2163, 4326, always_xy=True)

    x, y = to_2163.transform(lon, lat)
    lon_back, lat_back = from_2163.transform(x, y)

    # EPSG:2163 can emit inf for coordinates outside its natural region.
    # Those are valid transformation outputs (the CRS is not defined for
    # e.g. Australia); the invariant we want is "round-trip returns
    # original OR consistently marks the region as out-of-domain".
    import math
    if math.isinf(x) or math.isinf(y) or math.isnan(x) or math.isnan(y):
        return  # out-of-domain input; no round-trip guarantee

    if math.isinf(lon_back) or math.isnan(lon_back):
        return  # projection went off the map

    assert abs(lat - lat_back) < _TOLERANCE_DEG, (
        f"lat drift: {lat} → {lat_back}"
    )
    assert abs(lon - lon_back) < _TOLERANCE_DEG, (
        f"lon drift: {lon} → {lon_back}"
    )


@given(lat=_LAT, lon=_LON)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_nad83_roundtrip_identity(lat: float, lon: float) -> None:
    """WGS84 → EPSG:4269 (NAD83) → WGS84.

    NAD83 is the library's default `STORAGE_CRS` (see conf/defaults.py).
    NAD83 and WGS84 are geodetically very close but not identical — a
    round-trip drift within tolerance still holds; NAD83↔WGS84 datum
    shift is small (≤ 2 meters ≈ 2e-5 degrees at mid-latitudes) but
    non-zero, so we widen tolerance slightly for this pair.
    """
    to_nad83 = pyproj.Transformer.from_crs(4326, 4269, always_xy=True)
    from_nad83 = pyproj.Transformer.from_crs(4269, 4326, always_xy=True)

    x, y = to_nad83.transform(lon, lat)
    lon_back, lat_back = from_nad83.transform(x, y)

    # NAD83↔WGS84 datum shift: allow up to 2e-5 degrees (~2 meters)
    # of round-trip drift.
    nad83_tolerance = 2e-5

    assert abs(lat - lat_back) < nad83_tolerance, (
        f"lat drift: {lat} → {lat_back}"
    )
    assert abs(lon - lon_back) < nad83_tolerance, (
        f"lon drift: {lon} → {lon_back}"
    )
