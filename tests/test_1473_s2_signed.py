"""Regression coverage for uint64 S2 IDs stored in signed BIGINT columns."""

import sqlite3

import pytest

from siege_utilities.geo import grids, s2_utils


# s2sphere.CellId.from_lat_lng(LatLng.from_degrees(39, -98)).parent(12).
KANSAS_ID = 9773697741363347456
KANSAS_SIGNED_ID = -8673046332346204160
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1


def test_kansas_signed_round_trip_without_s2sphere(monkeypatch):
    monkeypatch.setattr(s2_utils, "S2_AVAILABLE", False)
    monkeypatch.setattr(s2_utils, "_s2", None)
    assert KANSAS_ID >> 61 == 4
    assert KANSAS_ID > INT64_MAX
    signed = s2_utils.s2_cell_id_to_int64(KANSAS_ID)
    assert INT64_MIN <= signed <= INT64_MAX
    assert signed == KANSAS_SIGNED_ID
    assert s2_utils.s2_cell_id_to_uint64(signed) == KANSAS_ID
    assert s2_utils.s2_cell_id_to_int64(signed) == signed


@pytest.mark.parametrize("raw", [0, 1, INT64_MAX, 1 << 63, KANSAS_ID, (1 << 64) - 1])
def test_conversion_preserves_all_64_bits(raw):
    signed = s2_utils.s2_cell_id_to_int64(raw)
    assert INT64_MIN <= signed <= INT64_MAX
    assert s2_utils.s2_cell_id_to_uint64(signed) == raw


@pytest.mark.parametrize("value", [INT64_MIN - 1, 1 << 64])
def test_out_of_range_integer_is_rejected(value):
    with pytest.raises(ValueError, match="64-bit"):
        s2_utils.s2_cell_id_to_int64(value)
    with pytest.raises(ValueError, match="64-bit"):
        s2_utils.s2_cell_id_to_uint64(value)


@pytest.mark.parametrize("value", [[KANSAS_ID], {"id": KANSAS_ID}])
def test_invalid_conversion_type_is_rejected(value):
    with pytest.raises(TypeError):
        s2_utils.s2_cell_id_to_int64(value)


@pytest.mark.parametrize("function", [
    s2_utils.s2_index_points,
    s2_utils.s2_index_polygon,
    s2_utils.s2_region_cover,
    s2_utils.s2_cells_to_ranges,
    s2_utils.s2_cell_id_to_uint64,
    grids.index_polygon,
])
def test_raw_id_documentation_identifies_uint64(function):
    assert "uint64" in function.__doc__
    assert "BIGINT" in function.__doc__


@pytest.fixture
def s2():
    return pytest.importorskip("s2sphere")


def test_kansas_id_matches_point_and_token(s2):
    cell = s2.CellId.from_lat_lng(s2.LatLng.from_degrees(39, -98)).parent(12)
    assert cell.face() == 4
    assert cell.id() == KANSAS_ID
    assert s2_utils.s2_cell_id_to_int64(cell.to_token()) == KANSAS_SIGNED_ID
    assert s2_utils.s2_cell_id_to_token(KANSAS_SIGNED_ID) == cell.to_token()


@pytest.mark.parametrize("cell_ids", [
    [KANSAS_ID],
    [(face << 61) + (1 << 60) for face in (0, 3, 4, 5)],
    [(1 << 63) - 1, (1 << 63) + 1],  # Leaf cells on either side of the sign bit.
    [],
])
def test_signed_sql_between_matches_unsigned_membership(s2, cell_ids):
    unsigned_ranges = s2_utils.s2_cells_to_ranges(cell_ids)
    signed_ranges = s2_utils.s2_cells_to_ranges(cell_ids, as_signed=True)
    signed_ids = [s2_utils.s2_cell_id_to_int64(cid) for cid in cell_ids]
    assert s2_utils.s2_cells_to_ranges(signed_ids) == unsigned_ranges
    assert s2_utils.s2_cells_to_ranges(signed_ids, as_signed=True) == signed_ranges
    assert len(signed_ranges) == len(unsigned_ranges)
    assert all(INT64_MIN <= lo <= hi <= INT64_MAX for lo, hi in signed_ranges)
    assert unsigned_ranges == [
        (s2_utils.s2_cell_id_to_uint64(lo), s2_utils.s2_cell_id_to_uint64(hi))
        for lo, hi in signed_ranges
    ]

    candidates = {1, KANSAS_ID - 1, KANSAS_ID + 1, (1 << 63) - 1, (1 << 63) + 1}
    for lo, hi in unsigned_ranges:
        candidates.update([lo - 2, lo, lo + 2, hi - 2, hi, hi + 2])
    candidates = sorted(cid for cid in candidates if s2.CellId(cid).is_valid())
    expected = {
        cid for cid in candidates
        if any(lo <= cid <= hi for lo, hi in unsigned_ranges)
    }
    connection = sqlite3.connect(":memory:", timeout=5.0)
    try:
        connection.execute("CREATE TABLE points (cell_id BIGINT)")
        connection.executemany(
            "INSERT INTO points VALUES (?)",
            [(s2_utils.s2_cell_id_to_int64(cid),) for cid in candidates],
        )
        selected = set()
        for bounds in signed_ranges:
            selected.update(
                s2_utils.s2_cell_id_to_uint64(row[0])
                for row in connection.execute(
                    "SELECT cell_id FROM points WHERE cell_id BETWEEN ? AND ?", bounds
                )
            )
        assert selected == expected
    finally:
        connection.close()


@pytest.mark.parametrize("level", [12, 30])
def test_signed_point_index_preserves_ids_and_series_index(s2, level):
    pd = pytest.importorskip("pandas")
    points = pd.DataFrame(
        {"lat": [39.0, 0.0, -80.0], "lon": [-98.0, 0.0, 0.0]},
        index=["kansas", "equator", "south"],
    )
    raw = s2_utils.s2_index_points(points, "lat", "lon", level, as_token=False)
    signed = s2_utils.s2_index_points(
        points, "lat", "lon", level, as_token=False, as_signed=True
    )
    expected = [
        s2.CellId.from_lat_lng(s2.LatLng.from_degrees(lat, lon)).parent(level).id()
        for lat, lon in zip(points["lat"], points["lon"])
    ]
    assert raw.tolist() == expected
    assert [s2_utils.s2_cell_id_to_uint64(cid) for cid in signed] == expected
    assert str(raw.dtype) == "uint64"
    assert str(signed.dtype) == "int64"
    assert signed.index.equals(points.index)
    assert signed.name == "s2_index"
    tokens = s2_utils.s2_index_points(points, "lat", "lon", level)
    assert all(isinstance(token, str) for token in tokens)
    with pytest.raises(ValueError, match="as_token"):
        s2_utils.s2_index_points(points, "lat", "lon", as_signed=True)


@pytest.mark.parametrize("refine", [True, False])
def test_signed_polygon_cover_round_trips(s2, refine):
    geometry = pytest.importorskip("shapely.geometry").box(-98.1, 38.9, -97.9, 39.1)
    raw = s2_utils.s2_index_polygon(geometry, level=10, refine=refine)
    signed = s2_utils.s2_index_polygon(geometry, level=10, refine=refine, as_signed=True)
    assert raw
    assert isinstance(signed, set)
    assert {s2_utils.s2_cell_id_to_uint64(cid) for cid in signed} == raw
    assert all(INT64_MIN <= cid <= INT64_MAX for cid in signed)


def test_signed_region_cover_round_trips(s2):
    geometry = pytest.importorskip("shapely.geometry").box(-98.1, 38.9, -97.9, 39.1)
    raw = s2_utils.s2_region_cover(geometry, max_cells=8)
    signed = s2_utils.s2_region_cover(geometry, max_cells=8, as_signed=True)
    assert raw
    assert [s2_utils.s2_cell_id_to_uint64(cid) for cid in signed] == raw
    assert s2_utils.s2_cells_to_ranges(signed, as_signed=True) == \
        s2_utils.s2_cells_to_ranges(raw, as_signed=True)


@pytest.mark.parametrize("cell_id", [0, 2, 6 << 61])
def test_ranges_reject_invalid_s2_cells(s2, cell_id):
    with pytest.raises(ValueError, match="Invalid S2 cell ID"):
        s2_utils.s2_cells_to_ranges([cell_id], as_signed=True)


def test_empty_points_preserve_integer_dtype(s2):
    pd = pytest.importorskip("pandas")
    points = pd.DataFrame(columns=["lat", "lon"])
    for as_signed, dtype in [(False, "uint64"), (True, "int64")]:
        result = s2_utils.s2_index_points(
            points, "lat", "lon", as_token=False, as_signed=as_signed
        )
        assert result.empty
        assert str(result.dtype) == dtype
        assert result.name == "s2_index"
        assert result.index.equals(points.index)


def test_postgis_guidance_explains_signed_storage():
    from siege_utilities.engines.dataframe_engine import PostGISEngine

    with pytest.raises(NotImplementedError) as error:
        PostGISEngine("postgresql://localhost/test").index_points(None, "lat", "lon")
    message = str(error.value)
    assert "uint64" in message
    assert "as_signed=True" in message
    assert "BIGINT" in message
