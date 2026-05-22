"""Tests for siege_utilities.geo.data_reception (SU#542)."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import zipfile

import pytest

from siege_utilities.geo.data_reception import (
    detect_format,
    extract_attributes_kml,
    extract_attributes_ogr,
    extract_attributes_swmaps,
)


def _write(tmp_path, name: str, content: bytes) -> str:
    p = os.path.join(tmp_path, name)
    with open(p, "wb") as fh:
        fh.write(content)
    return p


def test_detect_format_extension_map(tmp_path):
    cases = {
        "a.shp": "shapefile",
        "a.SHP": "shapefile",
        "a.geojson": "geojson",
        "a.kml": "kml",
        "a.kmz": "kmz",
        "a.gpkg": "geopackage",
        "a.dxf": "dxf",
        "a.swmz": "swmaps",
        "a.bin": "unknown",
        "a.txt": "unknown",
    }
    for name, expected in cases.items():
        p = _write(str(tmp_path), name, b"")
        assert detect_format(p) == expected, (name, expected)


def test_detect_format_geojson_peek(tmp_path):
    p = _write(
        str(tmp_path),
        "blob.json",
        b'{"type": "FeatureCollection", "features": []}',
    )
    assert detect_format(p) == "geojson"


def test_detect_format_random_json_is_unknown(tmp_path):
    p = _write(str(tmp_path), "blob.json", b'{"unrelated": true}')
    assert detect_format(p) == "unknown"


def test_detect_format_sqlite_swmaps(tmp_path):
    p = os.path.join(str(tmp_path), "field.sqlite")
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE features (uuid TEXT, name TEXT, layer_id TEXT)")
    conn.execute("CREATE TABLE points (fid TEXT, seq INT, lat REAL, lon REAL, elv REAL)")
    conn.execute("CREATE TABLE feature_layers (uuid TEXT, name TEXT, group_name TEXT, geom_type TEXT)")
    conn.commit()
    conn.close()
    assert detect_format(p) == "swmaps"


def test_detect_format_sqlite_non_swmaps(tmp_path):
    p = os.path.join(str(tmp_path), "other.sqlite")
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE unrelated (id INTEGER)")
    conn.commit()
    conn.close()
    assert detect_format(p) == "unknown"


def test_detect_format_zip_kmz(tmp_path):
    p = os.path.join(str(tmp_path), "thing.zip")
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("doc.kml", "<kml/>")
    assert detect_format(p) == "kmz"


def test_detect_format_zip_swmz_member(tmp_path):
    p = os.path.join(str(tmp_path), "thing.zip")
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("data.sqlite", b"")
    assert detect_format(p) == "swmaps"


def test_detect_format_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        detect_format("/nonexistent/path/x.shp")


def test_detect_format_directory_is_unknown(tmp_path):
    assert detect_format(str(tmp_path)) == "unknown"


# --- extract_attributes_ogr -----------------------------------------------


def test_extract_ogr_fiona_record_shape():
    feature = {"properties": {"NAME": "Travis", "GEOID": "48453"}, "geometry": {}}
    assert extract_attributes_ogr(feature, ["NAME"]) == "Travis"


def test_extract_ogr_candidate_fallback():
    feature = {"properties": {"GEOID20": "48453"}}
    assert extract_attributes_ogr(feature, ["GEOID", "GEOID20"]) == "48453"


def test_extract_ogr_missing_none_default():
    feature = {"properties": {"X": 1}}
    assert extract_attributes_ogr(feature, ["MISSING"]) is None


def test_extract_ogr_missing_raise():
    feature = {"properties": {}}
    with pytest.raises(KeyError):
        extract_attributes_ogr(feature, ["NAME"], missing="raise")


def test_extract_ogr_missing_invalid_token():
    with pytest.raises(ValueError):
        extract_attributes_ogr({"properties": {}}, ["X"], missing="bogus")


def test_extract_ogr_bare_dict_shape():
    feature = {"NAME": "X"}
    assert extract_attributes_ogr(feature, ["NAME"]) == "X"


def test_extract_ogr_none_feature():
    assert extract_attributes_ogr(None, ["X"]) is None


# --- extract_attributes_kml -----------------------------------------------


def test_extract_kml_present():
    data = {"depth": "3ft", "material": "PVC"}
    assert extract_attributes_kml(data, ["depth"]) == "3ft"


def test_extract_kml_candidate_fallback():
    data = {"MaterialType": "PVC"}
    assert extract_attributes_kml(data, ["Material", "MaterialType"]) == "PVC"


def test_extract_kml_missing_none():
    assert extract_attributes_kml({}, ["x"]) is None


def test_extract_kml_none_data():
    assert extract_attributes_kml(None, ["x"]) is None


# --- extract_attributes_swmaps --------------------------------------------


def _build_swmaps_sqlite(path: str, attr_rows):
    """attr_rows = list of (feature_id, field_name, value)."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE attribute_fields (uuid TEXT PRIMARY KEY, field_name TEXT);
        CREATE TABLE attribute_values (item_id TEXT, field_id TEXT, value TEXT);
        """
    )
    seen = {}
    for fid, fname, val in attr_rows:
        if fname not in seen:
            fuuid = f"fld-{len(seen)}"
            seen[fname] = fuuid
            conn.execute("INSERT INTO attribute_fields VALUES (?, ?)", (fuuid, fname))
        conn.execute(
            "INSERT INTO attribute_values VALUES (?, ?, ?)",
            (fid, seen[fname], val),
        )
    conn.commit()
    conn.close()


def test_extract_swmaps_present(tmp_path):
    p = os.path.join(str(tmp_path), "f.sqlite")
    _build_swmaps_sqlite(p, [("feat-1", "MATERIAL TYPE", "PVC")])
    assert extract_attributes_swmaps(p, "feat-1", ["MATERIAL TYPE"]) == "PVC"


def test_extract_swmaps_missing_returns_none(tmp_path):
    p = os.path.join(str(tmp_path), "f.sqlite")
    _build_swmaps_sqlite(p, [])
    assert extract_attributes_swmaps(p, "feat-1", ["MATERIAL TYPE"]) is None


def test_extract_swmaps_candidate_fallback(tmp_path):
    p = os.path.join(str(tmp_path), "f.sqlite")
    _build_swmaps_sqlite(p, [("feat-1", "DEPTH (FT)", "3.5")])
    assert (
        extract_attributes_swmaps(p, "feat-1", ["DEPTH", "DEPTH (FT)"]) == "3.5"
    )
