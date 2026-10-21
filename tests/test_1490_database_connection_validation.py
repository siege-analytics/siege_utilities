"""Regression coverage for loading stored database connections (#1490)."""

from pathlib import Path

import pytest
import yaml
from pydantic import SecretStr, ValidationError

from siege_utilities.config.models.database_connection import DatabaseConnection


DEFAULT_POSTGRES = {
    "name": "default_postgres",
    "connection_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "siege_analytics",
    "username": "postgres",
    "password": "password",
    "ssl_enabled": True,
    "connection_timeout": 30,
    "max_connections": 10,
}
DEFAULT_DUCKDB = {
    "name": "default_duckdb",
    "connection_type": "duckdb",
    "host": "localhost",
    "port": 0,
    "database": "siege_analytics.duckdb",
    "username": "",
    "password": "",
    "ssl_enabled": False,
    "connection_timeout": 30,
    "max_connections": 1,
}
CONFIG_DIR = Path(__file__).resolve().parents[1] / "siege_utilities" / "configs"


@pytest.mark.parametrize("entry", [DEFAULT_POSTGRES, DEFAULT_DUCKDB],
                         ids=["default_postgres", "default_duckdb"])
def test_shipped_default_connections_construct(entry):
    defaults = yaml.safe_load(
        (CONFIG_DIR / "default" / "database_connections.yaml").read_text()
    )
    assert entry in defaults["connections"]
    connection = DatabaseConnection(**entry)
    assert connection.name == entry["name"]
    assert isinstance(connection.password, SecretStr)
    assert connection.password.get_secret_value() == entry["password"]


@pytest.mark.parametrize("connection_type", ["postgresql", "mysql"])
@pytest.mark.parametrize("host,expected", [
    ("::1", "[::1]"),
    ("2001:db8::1", "[2001:db8::1]"),
    ("[::1]", "[::1]"),
    ("LOCALHOST", "localhost"),
])
def test_ipv6_and_localhost(connection_type, host, expected):
    connection = DatabaseConnection(**dict(
        DEFAULT_POSTGRES, connection_type=connection_type, host=host,
        password="ValidPass123", ssl_enabled=False,
    ))
    assert connection.host == ("localhost" if host == "LOCALHOST" else host)
    assert connection.get_connection_string() == (
        f"{connection_type}://postgres:ValidPass123@{expected}:5432/siege_analytics"
    )


@pytest.mark.parametrize("connection_type", ["duckdb", "sqlite"])
@pytest.mark.parametrize("database", [
    "data/analytics.db",
    "/data/client_a/analytics.duckdb",
    "./data with spaces/analytics-2026.db",
    "data/" + "archive/" * 8 + "analytics.db",
    r"C:\data\analytics.db",
    ":memory:",
])
@pytest.mark.parametrize("server_fields", [
    {},
    {"host": "", "port": 0, "username": "", "password": ""},
])
def test_file_connections_accept_paths_without_server_fields(
    connection_type, database, server_fields,
):
    connection = DatabaseConnection(
        name="local", connection_type=connection_type, database=database,
        **server_fields,
    )
    assert connection.get_connection_string() == f"{connection_type}:///{database}"
    assert connection.host == connection.username == ""
    assert connection.port == 0
    assert isinstance(connection.password, SecretStr)
    assert connection.password.get_secret_value() == ""


@pytest.mark.parametrize("password", [
    "password", "12345678", "qwerty123", "lowercase1", "UPPERCASE1",
    "NoDigitsHere", "x", "token-" + "a" * 800,
])
def test_stored_passwords_load_and_reload_without_strength_policy(password):
    connection = DatabaseConnection(**dict(DEFAULT_POSTGRES, password=password))
    restored = DatabaseConnection.model_validate(connection.model_dump())
    assert restored.password.get_secret_value() == password
    assert repr(SecretStr(password)) in repr(restored)


@pytest.mark.parametrize("connection_type", ["postgresql", "mysql"])
@pytest.mark.parametrize("field,empty", [
    ("host", ""), ("port", 0), ("username", ""), ("password", ""),
])
@pytest.mark.parametrize("omit", [False, True])
def test_server_connections_require_server_fields(connection_type, field, empty, omit):
    data = dict(DEFAULT_POSTGRES, connection_type=connection_type, password="ValidPass123")
    if omit:
        del data[field]
    else:
        data[field] = empty
    with pytest.raises(ValidationError):
        DatabaseConnection(**data)


@pytest.mark.parametrize("connection_type", ["postgresql", "mysql"])
@pytest.mark.parametrize("port", [1, 65535])
def test_server_port_boundaries(connection_type, port):
    connection = DatabaseConnection(**dict(
        DEFAULT_POSTGRES, connection_type=connection_type, port=port,
    ))
    assert connection.port == port


def test_assignment_keeps_secrets_wrapped_and_validates_connection_type():
    connection = DatabaseConnection(**DEFAULT_POSTGRES)
    connection.password = "short"
    assert isinstance(connection.password, SecretStr)
    assert connection.password.get_secret_value() == "short"
    assert "short" not in repr(connection)
    local = DatabaseConnection(name="local", connection_type="sqlite", database="db")
    with pytest.raises(ValidationError, match="Server host"):
        local.connection_type = "postgresql"


@pytest.mark.parametrize("field,value", [
    ("name", "bad name!"), ("connection_type", "oracle"),
    ("host", "bad host"), ("host", "2001:db8::invalid"),
    ("host", "[::1"), ("host", "[localhost]"),
    ("port", -1), ("port", 65536),
    ("database", "1badname"), ("database", "data/name.db"),
    ("database", "a" * 51), ("database", ""),
    ("username", "a" * 51), ("connection_timeout", 0),
    ("max_connections", 101), ("unknown_option", True),
])
def test_safe_constraints_remain(field, value):
    with pytest.raises(ValidationError):
        DatabaseConnection(**dict(DEFAULT_POSTGRES, password="ValidPass123", **{field: value}))


def test_hydra_loads_both_shipped_default_connections():
    pytest.importorskip("hydra")
    from siege_utilities.config.hydra_manager import HydraConfigManager

    with HydraConfigManager(config_dir=CONFIG_DIR) as manager:
        connections = manager.load_database_connections()
    assert [connection.name for connection in connections] == [
        "default_postgres", "default_duckdb",
    ]
    assert connections[0].password.get_secret_value() == "password"
    assert connections[1].get_connection_string() == "duckdb:///siege_analytics.duckdb"
