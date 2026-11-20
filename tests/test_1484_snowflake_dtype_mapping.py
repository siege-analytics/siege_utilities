"""Regression tests for the Snowflake auto-create dtype mapping (#1484).

Only ``SnowflakeConnector._map_pandas_to_snowflake_type`` is covered. Logical-type
loading and session-context restoration are deferred (#1484 items 2 and 3), and
identifier quoting belongs to #1421.
"""

from unittest.mock import Mock

import pytest

pd = pytest.importorskip("pandas")

from siege_utilities.analytics import snowflake_connector as sc  # noqa: E402

VARCHAR = "VARCHAR(16777216)"


@pytest.fixture
def connector(monkeypatch):
    monkeypatch.setattr(sc, "SNOWFLAKE_AVAILABLE", True)
    conn = sc.SnowflakeConnector(
        account="test_account", user="test_user",
        database="CONFIGURED_DB", schema="CONFIGURED_SCHEMA",
    )
    conn.connection = Mock()
    return conn


def _dtype(kind):
    """Build each pandas dtype from real data, as a DataFrame column would carry it."""
    builders = {
        "Int64": lambda: pd.array([1, None], dtype="Int64").dtype,
        "UInt8": lambda: pd.array([1, None], dtype="UInt8").dtype,
        "Float64": lambda: pd.array([1.5, None], dtype="Float64").dtype,
        "boolean": lambda: pd.array([True, None], dtype="boolean").dtype,
        "datetime64[ns, UTC]": lambda: pd.Series(pd.to_datetime(["2026-01-01"]).tz_localize("UTC")).dtype,
        "datetime64[ns, America/Chicago]": lambda: pd.Series(
            pd.to_datetime(["2026-01-01"]).tz_localize("America/Chicago")).dtype,
        "category[int]": lambda: pd.Series([1, 2], dtype="category").dtype,
        "category[float]": lambda: pd.Series([1.5, 2.5], dtype="category").dtype,
        "category[datetime, UTC]": lambda: pd.Series(
            pd.to_datetime(["2026-01-01"]).tz_localize("UTC"), dtype="category").dtype,
        "interval[int64]": lambda: pd.Series(pd.arrays.IntervalArray.from_breaks([0, 1, 2])).dtype,
        "int64": lambda: pd.Series([1, 2]).dtype,
        "uint8": lambda: pd.Series([1], dtype="uint8").dtype,
        "float64": lambda: pd.Series([1.5]).dtype,
        "bool": lambda: pd.Series([True]).dtype,
        "datetime64[ns]": lambda: pd.Series(pd.to_datetime(["2026-01-01"])).dtype,
        "timedelta64[ns]": lambda: pd.Series(pd.to_timedelta(["1s"])).dtype,
        "object": lambda: pd.Series(["text", None]).dtype,
        "string": lambda: pd.Series(["text"], dtype="string").dtype,
        "category[str]": lambda: pd.Series(["a", "b"], dtype="category").dtype,
        "period[M]": lambda: pd.Series(pd.period_range("2026-01", periods=1, freq="M")).dtype,
    }
    return builders[kind]()


# Fails on v4.0.0: substring matching on the dtype name sent these to the wrong type.
CORRECTED = [
    ("Int64", "NUMBER(38,0)"),             # v4.0.0: VARCHAR ("Int64" has no lowercase "int")
    ("UInt8", "NUMBER(38,0)"),             # v4.0.0: VARCHAR
    ("Float64", "FLOAT"),                  # v4.0.0: VARCHAR
    ("datetime64[ns, UTC]", "TIMESTAMP_TZ"),             # v4.0.0: TIMESTAMP_NTZ (offset dropped)
    ("datetime64[ns, America/Chicago]", "TIMESTAMP_TZ"),  # v4.0.0: TIMESTAMP_NTZ
    ("category[int]", "NUMBER(38,0)"),     # v4.0.0: VARCHAR
    ("category[float]", "FLOAT"),          # v4.0.0: VARCHAR
    ("category[datetime, UTC]", "TIMESTAMP_TZ"),  # v4.0.0: VARCHAR
    ("interval[int64]", VARCHAR),          # v4.0.0: NUMBER(38,0) ("interval[int64, right]" contains "int")
]

# Already correct on v4.0.0 and unchanged.
UNCHANGED = [
    ("int64", "NUMBER(38,0)"),
    ("uint8", "NUMBER(38,0)"),
    ("float64", "FLOAT"),
    ("bool", "BOOLEAN"),
    ("boolean", "BOOLEAN"),
    ("datetime64[ns]", "TIMESTAMP_NTZ"),
    ("timedelta64[ns]", VARCHAR),  # deliberate: no interval column type; loading is #1484 item 2
    ("object", VARCHAR),
    ("string", VARCHAR),
    ("category[str]", VARCHAR),
    ("period[M]", VARCHAR),
]


@pytest.mark.parametrize("kind, expected", CORRECTED)
def test_mapping_corrects_v400_misclassified_dtypes(connector, kind, expected):
    assert connector._map_pandas_to_snowflake_type(_dtype(kind)) == expected


@pytest.mark.parametrize("kind, expected", UNCHANGED)
def test_mapping_keeps_v400_types_that_were_already_right(connector, kind, expected):
    assert connector._map_pandas_to_snowflake_type(_dtype(kind)) == expected


def test_auto_create_uses_the_mapped_types(connector):
    # The mapping feeds CREATE TABLE: a nullable integer column must be numeric.
    connector.cursor = Mock()
    df = pd.DataFrame({
        "votes": pd.array([12000, None], dtype="Int64"),
        "at": pd.Series(pd.to_datetime(["2026-01-01", None]).tz_localize("UTC")),
    })

    connector._create_table_from_dataframe(df, "RESULTS", overwrite=False)

    create = connector.cursor.execute.call_args_list[-1].args[0]
    assert '"votes" NUMBER(38,0)' in create
    assert '"at" TIMESTAMP_TZ' in create
