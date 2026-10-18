"""Live PostGIS SQL parity for NULL groups and aggregates (#1454)."""

import os

import pytest

from siege_utilities.engines.dataframe_engine import PostGISEngine
from tests.test_engines_groupby_agg_nulls import _rows

pytestmark = pytest.mark.postgis


@pytest.mark.parametrize("agg", ["sum", "count", "mean", "min", "max"])
def test_postgis_null_groups_agree_with_live_sql(agg):
    dsn = os.environ.get("SIEGE_UTILITIES_TEST_PG_DSN")
    if not dsn:
        pytest.skip("Set SIEGE_UTILITIES_TEST_PG_DSN to run live PostGIS parity")
    backend = PostGISEngine(dsn)
    sql_fn = "avg" if agg == "mean" else agg
    # VALUES avoids creating persistent tables in the shared test database.
    source = """
        SELECT * FROM (VALUES
            (NULL::text, NULL::double precision), (NULL, 2), (NULL, 4),
            ('empty', NULL), ('empty', NULL),
            ('partial', NULL), ('partial', 5), ('partial', 7), ('partial', NULL),
            ('full', 3), ('full', 9), ('zero', 2), ('zero', -2)
        ) AS input_frame(key, value)
    """
    try:
        assert (
            backend.query("SELECT PostGIS_Version() AS version")["version"]
            .notna()
            .all()
        )
        frame = backend.query(source)
        expected = backend.query(
            f"SELECT key, {sql_fn}(value) AS value FROM ({source}) AS input_rows GROUP BY key"
        )
        result = backend.groupby_agg(frame, ["key"], {"value": agg})
        assert _rows(result) == _rows(expected)
    finally:
        backend._sql_engine.dispose()
