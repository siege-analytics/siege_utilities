"""End-to-end distributed export pipeline on a real SparkSession.

Exercises, together and against real Spark + real on-disk round-trips, the
distributed fixes from this sweep:
- synthetic generators return exactly the requested row count (#1310/#1311)
- prepare_dataframe_for_export handles boolean/date/timestamp columns without
  raising, rendering every column as a string (#1319/#1320)
- a genuine CSV and parquet write -> read round-trip through the public export
  helpers (net-new: the suite previously only mock-tested these writers)

Uses the session-scoped ``real_spark_session`` fixture (skips cleanly when
pyspark is absent) and ``tmp_path`` for scratch output.
"""

from datetime import date, datetime

import pytest

from siege_utilities import generate_synthetic_population
from siege_utilities import generate_synthetic_businesses
from siege_utilities import generate_synthetic_housing
from siege_utilities import prepare_dataframe_for_export
from siege_utilities import export_prepared_df_as_csv_to_path_using_delimiter
from siege_utilities import write_df_to_parquet
from siege_utilities import read_parquet_to_df


def _mixed_type_rows(n):
    from pyspark.sql import Row

    return [
        Row(
            flag=(i % 2 == 0),
            d=date(2020, 1, 1 + i),
            ts=datetime(2020, 1, 1, 12, i),
            n=i,
            x=float(i) + 0.5,
            name=f"r{i}",
        )
        for i in range(n)
    ]


@pytest.mark.e2e
class TestExportPipelineE2E:
    def test_synthetic_generators_produce_exact_counts(self):
        assert len(generate_synthetic_population(size=25)) == 25
        assert len(generate_synthetic_businesses(business_count=12)) == 12
        assert len(generate_synthetic_housing(housing_count=7)) == 7

    def test_mixed_type_dataframe_csv_roundtrip(
        self, real_spark_session, tmp_path
    ):
        sdf = real_spark_session.createDataFrame(_mixed_type_rows(6))

        # prepare_dataframe_for_export must not raise on the boolean/date/
        # timestamp columns, and renders every column as a string.
        prepared = prepare_dataframe_for_export(sdf)
        assert all(dtype == "string" for _, dtype in prepared.dtypes)

        out = tmp_path / "csv_out"
        export_prepared_df_as_csv_to_path_using_delimiter(prepared, out)

        back = real_spark_session.read.option("header", "true").csv(str(out))
        assert back.count() == 6
        assert set(back.columns) == {"flag", "d", "ts", "n", "x", "name"}
        # the boolean column survived the round-trip as its string rendering.
        assert {r["flag"] for r in back.select("flag").collect()} == {
            "true",
            "false",
        }

    def test_parquet_roundtrip_preserves_schema(
        self, real_spark_session, tmp_path
    ):
        sdf = real_spark_session.createDataFrame(_mixed_type_rows(6))

        parquet_path = tmp_path / "pq"
        write_df_to_parquet(sdf, str(parquet_path))
        back = read_parquet_to_df(real_spark_session, str(parquet_path))

        assert back.count() == 6
        # parquet is typed, so the schema round-trips exactly.
        assert dict(back.dtypes) == dict(sdf.dtypes)
