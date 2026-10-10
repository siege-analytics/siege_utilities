"""End-to-end pandas <-> Spark bridge round-trip on a real SparkSession.

Net-new coverage for the dataframe_bridge conversion helpers, which were
previously untested. Despite living under the ``databricks`` package they carry
no Databricks-runtime dependency -- they are thin pandas/pyspark conversions
that run against any SparkSession.

Uses the session-scoped ``real_spark_session`` fixture (skips cleanly when
pyspark is absent).
"""

import pandas as pd
import pytest

from siege_utilities import pandas_to_spark
from siege_utilities import spark_to_pandas


@pytest.mark.e2e
class TestDataframeBridgeE2E:
    def _frame(self):
        return pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["a", "b", "c"],
                "val": [1.5, 2.5, 3.5],
            }
        )

    def test_pandas_spark_pandas_round_trip(self, real_spark_session):
        pdf = self._frame()

        sdf = pandas_to_spark(pdf, real_spark_session)
        assert sdf.count() == 3
        assert set(sdf.columns) == {"id", "name", "val"}

        back = spark_to_pandas(sdf)
        assert isinstance(back, pd.DataFrame)
        assert back.shape == (3, 3)
        # the data survives the full round-trip unchanged.
        lhs = back.sort_values("id").reset_index(drop=True)
        rhs = pdf.sort_values("id").reset_index(drop=True)
        assert lhs.equals(rhs)

    def test_spark_to_pandas_honours_limit(self, real_spark_session):
        sdf = pandas_to_spark(self._frame(), real_spark_session)

        limited = spark_to_pandas(sdf, limit=2)
        assert isinstance(limited, pd.DataFrame)
        assert len(limited) == 2
