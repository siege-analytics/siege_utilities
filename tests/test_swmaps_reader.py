"""Tests for siege_utilities.geo.swmaps_reader (SU#544)."""

from __future__ import annotations

import os
import sqlite3
import zipfile

import pytest

pytest.importorskip("shapely")

from siege_utilities.geo.swmaps_reader import (
    open_swmaps,
    read_features,
)


def _build_swmaps_sqlite(
    db_path: str,
    features,  # list of (fid, name, layer_id, layer_name, group, geom_type, [(seq, lat, lon, elv), ...])
    attributes=None,  # list of (fid, field_name, value)
):
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE features (uuid TEXT, name TEXT, layer_id TEXT);
        CREATE TABLE points (fid TEXT, seq INTEGER, lat REAL, lon REAL, elv REAL);
        CREATE TABLE feature_layers (uuid TEXT, name TEXT, group_name TEXT, geom_type TEXT);
        CREATE TABLE attribute_fields (uuid TEXT PRIMARY KEY, field_name TEXT);
        CREATE TABLE attribute_values (item_id TEXT, field_id TEXT, value TEXT);
        """
    )
    seen_layers = {}
    for fid, fname, layer_id, layer_name, group, geom_type, coords in features:
        conn.execute("INSERT INTO features VALUES (?, ?, ?)", (fid, fname, layer_id))
        if layer_id not in seen_layers:
            conn.execute(
                "INSERT INTO feature_layers VALUES (?, ?, ?, ?)",
                (layer_id, layer_name, group, geom_type),
            )
            seen_layers[layer_id] = True
        for seq, lat, lon, elv in coords:
            conn.execute(
                "INSERT INTO points VALUES (?, ?, ?, ?, ?)",
                (fid, seq, lat, lon, elv),
            )

    seen_fields: dict[str, str] = {}
    for fid, fname, val in attributes or []:
        if fname not in seen_fields:
            fuuid = f"fld-{len(seen_fields)}"
            seen_fields[fname] = fuuid
            conn.execute(
                "INSERT INTO attribute_fields VALUES (?, ?)", (fuuid, fname)
            )
        conn.execute(
            "INSERT INTO attribute_values VALUES (?, ?, ?)",
            (fid, seen_fields[fname], val),
        )
    conn.commit()
    conn.close()


def test_open_sqlite_direct(tmp_path):
    db = os.path.join(str(tmp_path), "raw.sqlite")
    _build_swmaps_sqlite(db, [])
    with open_swmaps(db) as archive:
        assert archive.db_path == db


def test_open_swmz_archive(tmp_path):
    inner = os.path.join(str(tmp_path), "inner.sqlite")
    _build_swmaps_sqlite(inner, [])
    archive_path = os.path.join(str(tmp_path), "field.swmz")
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.write(inner, arcname="data.sqlite")

    extracted_path = None
    with open_swmaps(archive_path) as archive:
        extracted_path = archive.db_path
        assert extracted_path.endswith("data.sqlite")
        assert os.path.exists(extracted_path)
    # After context exit, temp dir should be cleaned.
    assert not os.path.exists(extracted_path)


def test_open_missing_raises():
    with pytest.raises(FileNotFoundError):
        open_swmaps("/nonexistent/x.swmz")


def test_open_unrecognized_extension(tmp_path):
    p = os.path.join(str(tmp_path), "x.txt")
    open(p, "w").close()
    with pytest.raises(ValueError, match="Unrecognized"):
        open_swmaps(p)


def test_open_archive_without_sqlite_member(tmp_path):
    p = os.path.join(str(tmp_path), "empty.swmz")
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("readme.txt", "nothing here")
    with pytest.raises(ValueError, match="no .sqlite"):
        open_swmaps(p)


def test_read_features_point_and_linestring(tmp_path):
    db = os.path.join(str(tmp_path), "data.sqlite")
    _build_swmaps_sqlite(
        db,
        features=[
            ("feat-1", "Hydrant 1", "lyr-1", "Hydrant", "Water", "point",
             [(0, 30.0, -97.0, 100.0)]),
            ("feat-2", "Main 1", "lyr-2", "Water Main", "Water", "linestring",
             [(0, 30.0, -97.0, 100.0),
              (1, 30.1, -97.1, 101.0),
              (2, 30.2, -97.2, 102.0)]),
        ],
    )
    with open_swmaps(db) as archive:
        records = list(read_features(archive))

    assert len(records) == 2
    by_id = {r["feature_id"]: r for r in records}
    assert by_id["feat-1"]["geometry_wkt"].startswith("POINT")
    assert by_id["feat-2"]["geometry_wkt"].startswith("LINESTRING")
    assert by_id["feat-1"]["feature_type"] == "Hydrant"
    assert by_id["feat-2"]["feature_group"] == "Water"


def test_read_features_drops_z_when_elv_missing(tmp_path):
    db = os.path.join(str(tmp_path), "data.sqlite")
    _build_swmaps_sqlite(
        db,
        features=[
            ("f1", "x", "lyr", "T", "G", "linestring",
             [(0, 30.0, -97.0, 100.0),
              (1, 30.1, -97.1, None)]),  # Z missing on one
        ],
    )
    with open_swmaps(db) as archive:
        records = list(read_features(archive))
    # 2D LINESTRING — no 'Z' in WKT.
    assert records[0]["geometry_wkt"].startswith("LINESTRING (")
    assert " Z" not in records[0]["geometry_wkt"][:15]


def test_read_features_includes_z_when_all_present(tmp_path):
    db = os.path.join(str(tmp_path), "data.sqlite")
    _build_swmaps_sqlite(
        db,
        features=[
            ("f1", "x", "lyr", "T", "G", "point",
             [(0, 30.0, -97.0, 100.0)]),
        ],
    )
    with open_swmaps(db) as archive:
        records = list(read_features(archive))
    # 3D POINT — shapely emits "POINT Z (...)".
    assert "Z" in records[0]["geometry_wkt"].split("(")[0]


def test_read_features_attributes_verbatim(tmp_path):
    db = os.path.join(str(tmp_path), "data.sqlite")
    _build_swmaps_sqlite(
        db,
        features=[
            ("f1", "x", "lyr", "T", "G", "point",
             [(0, 30.0, -97.0, 100.0)]),
        ],
        attributes=[
            ("f1", "MATERIAL TYPE", "PVC"),
            ("f1", "DEPTH (FT)", "3.5"),
        ],
    )
    with open_swmaps(db) as archive:
        records = list(read_features(archive))
    assert records[0]["attributes"] == {
        "MATERIAL TYPE": "PVC",
        "DEPTH (FT)": "3.5",
    }


def test_read_features_attributes_with_mapper(tmp_path):
    db = os.path.join(str(tmp_path), "data.sqlite")
    _build_swmaps_sqlite(
        db,
        features=[
            ("f1", "x", "lyr", "T", "G", "point",
             [(0, 30.0, -97.0, 100.0)]),
        ],
        attributes=[
            ("f1", "MATERIAL TYPE", "PVC"),
            ("f1", "DEPTH (FT)", "3.5"),
        ],
    )
    mapper = {"MATERIAL TYPE": "material", "DEPTH (FT)": "depth_to_top"}
    with open_swmaps(db) as archive:
        records = list(read_features(archive, mapper=mapper))
    assert records[0]["attributes"] == {"material": "PVC", "depth_to_top": "3.5"}


def test_swmaps_archive_close_idempotent(tmp_path):
    db = os.path.join(str(tmp_path), "data.sqlite")
    _build_swmaps_sqlite(db, [])
    arch = open_swmaps(db)
    arch.close()
    arch.close()  # second call must not raise
    with pytest.raises(ValueError):
        _ = arch.db_path
