"""SparkEngine.from_geodataframe reads CRS only from a real GeoDataFrame (#1852).

A plain DataFrame with a column named ``crs`` has no CRS: attribute access
would return that column, so the no-CRS warning must still fire and the column
must be serialized as ordinary data.
"""

import logging
from types import SimpleNamespace

import pandas as pd
import pytest

pytest.importorskip("geopandas")
from shapely.geometry import Point

from siege_utilities.engines.dataframe_engine import SparkEngine


def _engine(captured: dict) -> SparkEngine:
    # Bypass __init__ so no JVM is needed; createDataFrame records its input.
    engine = SparkEngine.__new__(SparkEngine)
    engine._spark = SimpleNamespace(createDataFrame=lambda pdf: captured.setdefault("pdf", pdf))
    return engine


def test_plain_dataframe_with_crs_column_still_warns(caplog: pytest.LogCaptureFixture) -> None:
    captured: dict = {}
    frame = pd.DataFrame({"pid": [1], "crs": ["EPSG:3857"], "geometry": [Point(5, 6)]})

    with caplog.at_level(logging.WARNING, logger="siege_utilities.engines.dataframe_engine"):
        _engine(captured).from_geodataframe(frame)

    assert any("no CRS" in record.getMessage() for record in caplog.records)
    pdf = captured["pdf"]
    assert pdf["crs"].tolist() == ["EPSG:3857"]
    assert pdf["geometry"].tolist() == ["POINT (5 6)"]
