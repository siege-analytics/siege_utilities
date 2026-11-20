"""Regression coverage for the Spark JDBC driver defaults in issue #1483."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from siege_utilities.config import databases
from siege_utilities.conf import settings


@pytest.fixture(autouse=True)
def jdbc_settings():
    """Keep project settings from changing the defaults under test."""
    with settings.override(SPARK_JDBC_PACKAGES=None):
        yield


@pytest.fixture
def spark_builder(monkeypatch):
    """Capture Spark builder options without starting a JVM or resolving jars."""
    builder = MagicMock()
    builder.appName.return_value = builder
    builder.config.return_value = builder
    pyspark = ModuleType("pyspark")
    sql = ModuleType("pyspark.sql")
    sql.SparkSession = SimpleNamespace(builder=builder)
    pyspark.sql = sql
    monkeypatch.setitem(sys.modules, "pyspark", pyspark)
    monkeypatch.setitem(sys.modules, "pyspark.sql", sql)
    return builder


@pytest.fixture
def load_config(monkeypatch):
    loader = MagicMock(side_effect=lambda name, directory: {"connection_type": name})
    monkeypatch.setattr(databases, "load_database_config", loader)
    return loader


def configured_packages(builder):
    values = [
        call.args[1]
        for call in builder.config.call_args_list
        if call.args[0] == "spark.jars.packages"
    ]
    assert len(values) <= 1
    return values[0].split(",") if values else []


def test_default_drivers_are_patched(spark_builder, load_config):
    spark = databases.create_spark_session_with_databases(
        "jdbc-regression", ["postgres", "mysql", "oracle"], "db-configs"
    )

    packages = configured_packages(spark_builder)
    postgres = [p for p in packages if p.startswith("org.postgresql:postgresql:")]
    mysql = [p for p in packages if p.startswith("com.mysql:mysql-connector-j:")]
    oracle = [p for p in packages if p.startswith("com.oracle.database.jdbc:ojdbc")]
    assert len(postgres) == 1
    assert tuple(map(int, postgres[0].split(":")[-1].split("."))) >= (42, 7, 2)
    assert len(mysql) == 1
    assert tuple(map(int, mysql[0].split(":")[-1].split("."))) >= (8, 2, 0)
    assert len(oracle) == 1
    assert tuple(map(int, oracle[0].split(":")[-1].split("."))) >= (23, 0)
    assert len(packages) == 3
    assert "org.postgresql:postgresql:42.3.1" not in packages
    assert not any(p.startswith("mysql:mysql-connector-java:") for p in packages)
    assert "com.oracle.database.jdbc:ojdbc8:21.1.0.0" not in packages
    load_config.assert_any_call("postgres", "db-configs")
    spark_builder.appName.assert_called_once_with("jdbc-regression")
    spark_builder.config.assert_any_call("spark.sql.adaptive.enabled", "true")
    spark_builder.getOrCreate.assert_called_once_with()
    assert spark is spark_builder.getOrCreate.return_value


@pytest.mark.parametrize(
    "connection_type, coordinate_prefix",
    [
        ("POSTGRES", "org.postgresql:postgresql:"),
        ("mysql", "com.mysql:mysql-connector-j:"),
        ("oracle", "com.oracle.database.jdbc:ojdbc"),
    ],
)
def test_only_requested_driver_is_added(
    connection_type, coordinate_prefix, spark_builder, load_config
):
    databases.create_spark_session_with_databases(database_names=[connection_type])

    packages = configured_packages(spark_builder)
    assert len(packages) == 1
    assert packages[0].startswith(coordinate_prefix)


@pytest.mark.parametrize("database_names", [None, []])
def test_no_database_adds_no_driver(database_names, spark_builder, load_config):
    databases.create_spark_session_with_databases(database_names=database_names)

    assert configured_packages(spark_builder) == []
    load_config.assert_not_called()


@pytest.mark.parametrize("database_names", [None, [], ["postgres", "mysql"]])
@pytest.mark.parametrize(
    "override", [[], ["org.postgresql:postgresql:42.7.2", "com.mysql:mysql-connector-j:8.4.0"]]
)
def test_override_replaces_defaults(database_names, override, spark_builder, load_config):
    original = list(override)
    with settings.override(SPARK_JDBC_PACKAGES=override):
        databases.create_spark_session_with_databases(database_names=database_names)

    assert configured_packages(spark_builder) == original
    assert override == original
    load_config.assert_not_called()


@pytest.mark.parametrize(
    "override, expected",
    [
        ("", []),
        (
            "org.postgresql:postgresql:42.7.2, com.mysql:mysql-connector-j:8.4.0",
            ["org.postgresql:postgresql:42.7.2", "com.mysql:mysql-connector-j:8.4.0"],
        ),
    ],
)
def test_comma_separated_override(override, expected, spark_builder, load_config):
    with settings.override(SPARK_JDBC_PACKAGES=override):
        databases.create_spark_session_with_databases(database_names=["postgres"])

    assert configured_packages(spark_builder) == expected


@pytest.mark.parametrize(
    "config, message",
    [({}, "missing 'connection_type'"), ({"connection_type": "unknown"}, "Unsupported connection_type")],
)
def test_invalid_config_still_raises(config, message, spark_builder, load_config):
    load_config.side_effect = None
    load_config.return_value = config

    with pytest.raises(ValueError, match=message):
        databases.create_spark_session_with_databases(database_names=["invalid"])

    spark_builder.getOrCreate.assert_not_called()
