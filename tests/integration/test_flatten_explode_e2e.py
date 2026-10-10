"""End-to-end flatten-and-explode pipeline on a real SparkSession.

Regression guard for #1321/#1322: when ``explode_arrays=True``,
flatten_json_column_and_join_back_to_df must explode only columns whose
top-level type is an array. The previous implementation selected columns by a
substring match on the dtype string (``'array' in data_type.lower()``), which
also matched struct columns whose nested schema merely mentions an array -- for
example a ``struct<items:array<bigint>>`` column -- and then crashed trying to
``explode()`` a struct.

The fixture below is built precisely to trip that bug: the parsed JSON has a
genuine top-level array (``tags``) alongside a struct that itself contains an
array (``meta.items``). The struct column's dtype string contains the substring
``array``, so the pre-fix code would have tried to explode it and raised.

Uses the session-scoped ``real_spark_session`` fixture (skips cleanly when
pyspark is absent).
"""

import pytest

from siege_utilities import flatten_json_column_and_join_back_to_df


_PAYLOAD = '{"tags":["x","y"],"meta":{"items":[1,2]},"n":5}'


@pytest.mark.e2e
class TestFlattenExplodeE2E:
    def test_explode_arrays_skips_struct_columns(
        self, real_spark_session, tmp_path
    ):
        from pyspark.sql import Row

        df = real_spark_session.createDataFrame(
            [Row(id=1, payload=_PAYLOAD)]
        )
        assert df.count() == 1

        out = flatten_json_column_and_join_back_to_df(
            df,
            "payload",
            explode_arrays=True,
            show_samples=False,
            verbose=False,
        )

        # the genuine top-level array multiplied the single input row into one
        # row per element; the pre-fix crash on the struct column would prevent
        # reaching this assertion at all.
        assert out.count() == 2

        dtypes = dict(out.dtypes)
        # the struct column (dtype string contains the substring "array") was
        # preserved, not exploded -- this is the exact #1322 guard.
        assert dtypes["json_column_meta"].startswith("struct")
        assert "array" in dtypes["json_column_meta"]

        # the genuine array column was exploded to its scalar elements.
        tags = {r["json_column_tags"] for r in out.select(
            "json_column_tags"
        ).collect()}
        assert tags == {"x", "y"}

        # the non-array scalar survived on every exploded row.
        assert {r["json_column_n"] for r in out.select(
            "json_column_n"
        ).collect()} == {5}
