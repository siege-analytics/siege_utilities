"""Contract for flatten_json_column_and_join_back_to_df explode_arrays path.

Regression for the defect where explode_arrays=True selected columns by a
substring match on the dtype string ('array' in data_type), which matched the
intermediate parsed_json struct column and raised on explode(). Uses the
real_spark_session fixture, which skips cleanly when pyspark is unavailable.
"""

from siege_utilities import flatten_json_column_and_join_back_to_df


def test_explode_arrays_expands_array_field(real_spark_session):
    df = real_spark_session.createDataFrame(
        [(1, '{"tags":[10,20,30],"n":"x"}')],
        ["id", "payload"],
    )
    result = flatten_json_column_and_join_back_to_df(
        df, "payload", explode_arrays=True, show_samples=False
    )
    rows = result.collect()
    # The single array of three elements explodes into three rows.
    assert len(rows) == 3
    tag_col = next(c for c in result.columns if c.endswith("tags"))
    assert sorted(r[tag_col] for r in rows) == [10, 20, 30]
    # The non-array scalar field is preserved on every exploded row.
    n_col = next(c for c in result.columns if c.endswith("n"))
    assert all(r[n_col] == "x" for r in rows)


def test_explode_arrays_ignores_non_array_columns(real_spark_session):
    # No array fields: explode_arrays=True must be a no-op, not a crash.
    df = real_spark_session.createDataFrame(
        [(1, '{"a":1,"b":"y"}')],
        ["id", "payload"],
    )
    result = flatten_json_column_and_join_back_to_df(
        df, "payload", explode_arrays=True, show_samples=False
    )
    assert result.count() == 1
