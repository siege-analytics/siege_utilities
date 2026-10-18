"""Exercise literal escaping with Spark's real SQL parser and evaluator."""

import pytest

from siege_utilities.core.sql_safety import escape_sql_string_literal
from siege_utilities.engines.dataframe_engine import SparkEngine


pytestmark = pytest.mark.requires_spark


@pytest.fixture(scope="module")
def spark_literals(real_spark_session):
    spark = real_spark_session.newSession()
    spark.conf.set("spark.sql.parser.escapedStringLiterals", "false")
    return spark


@pytest.mark.parametrize("dialect", ["spark", "hive", "databricks", "snowflake"])
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(r"\' AS x, 1+1 AS injected --", id="injection"),
        pytest.param(r"a\b", id="backslash"),
        pytest.param("O'Brien", id="quote"),
        pytest.param("trailing\\", id="trailing-backslash"),
        pytest.param("", id="empty"),
    ],
)
def test_sql_literal_round_trip(spark_literals, dialect, value):
    escaped = escape_sql_string_literal(value, dialect=dialect)
    result = spark_literals.sql(f"SELECT '{escaped}' AS value")

    assert result.columns == ["value"]
    assert [tuple(row) for row in result.collect()] == [(value,)]


@pytest.fixture(scope="module")
def distance_engine(spark_literals):
    spark = spark_literals.newSession()
    # Echo spatial arguments so arbitrary (non-WKT) attack strings reach the
    # real SQL parser and evaluator without requiring Sedona's WKT parser.
    spark.udf.register("ST_GeomFromText", lambda value: value, "string")
    spark.udf.register("ST_Distance", lambda left, right: right, "string")
    return SparkEngine(spark=spark)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(r"\' AS x, 1+1 AS injected --", id="injection"),
        pytest.param(r"a\b", id="backslash"),
    ],
)
def test_distance_literal_round_trip(distance_engine, value):
    df = distance_engine._session.sql("SELECT 'POINT(0 0)' AS geometry")

    result = distance_engine.distance(df, value)

    assert result.columns == ["geometry", "_distance"]
    assert [tuple(row) for row in result.select("_distance").collect()] == [(value,)]
