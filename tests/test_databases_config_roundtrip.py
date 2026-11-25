"""Regression coverage for database config round-tripping (#1476)."""

import inspect
import json
import logging
import re

import pytest

from siege_utilities.config.databases import (
    create_database_config,
    get_spark_database_options,
    load_database_config,
    save_database_config,
)


@pytest.mark.parametrize(
    ("name", "env_name"),
    [
        ("analytics-db", "DB_ANALYTICS_DB_PASSWORD"),
        ("prod.replica", "DB_PROD_REPLICA_PASSWORD"),
        ("my db", "DB_MY_DB_PASSWORD"),
        ("café", "DB_CAF__PASSWORD"),
        ("123_db", "DB_123_DB_PASSWORD"),
    ],
)
def test_password_roundtrip_uses_reported_env_var(
    name, env_name, tmp_path, monkeypatch, caplog,
):
    config = create_database_config(
        name, "postgres", "localhost", 5432, "db", "user", "original-secret",
    )
    # Django's disable_existing_loggers must not make the caplog assertions
    # below vacuous or empty in a randomized full run (#2053).
    monkeypatch.setattr(logging.getLogger("siege_utilities"), "disabled", False)
    caplog.set_level(logging.WARNING, logger="siege_utilities")
    save_database_config(config, str(tmp_path))

    saved_text = (tmp_path / f"database_{name}.json").read_text()
    saved = json.loads(saved_text)
    assert saved["password"] == f"${{{env_name}}}"
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", env_name)
    assert f"${{{env_name}}}" in caplog.text
    assert "original-secret" not in saved_text + caplog.text
    assert config["password"] == "original-secret"

    monkeypatch.setenv(env_name, "resolved-secret")
    loaded = load_database_config(name, str(tmp_path))
    assert loaded["password"] == "resolved-secret"
    assert get_spark_database_options(name, str(tmp_path))["password"] == "resolved-secret"


def test_missing_saved_password_env_var_raises(tmp_path, monkeypatch):
    config = create_database_config(
        "analytics-db", "postgres", "localhost", 5432, "db", "user", "secret",
    )
    save_database_config(config, str(tmp_path))
    monkeypatch.delenv("DB_ANALYTICS_DB_PASSWORD", raising=False)
    monkeypatch.delenv("DB_ANALYTICS-DB_PASSWORD", raising=False)

    with pytest.raises(EnvironmentError, match="DB_ANALYTICS_DB_PASSWORD"):
        load_database_config("analytics-db", str(tmp_path))


@pytest.mark.parametrize("reference", ["${DB_ANALYTICS-DB_PASSWORD}", "${BAD.NAME}"])
def test_invalid_legacy_password_reference_raises(reference, tmp_path, monkeypatch):
    monkeypatch.delenv(reference[2:-1], raising=False)
    (tmp_path / "database_legacy.json").write_text(json.dumps({"password": reference}))

    with pytest.raises(ValueError, match="password environment variable reference"):
        load_database_config("legacy", str(tmp_path))


@pytest.mark.parametrize("ssl_mode", ["require", "verify-full"])
@pytest.mark.parametrize("connection_type", ["postgres", "POSTGRES"])
def test_ssl_mode_reaches_spark_options(ssl_mode, connection_type, tmp_path, monkeypatch):
    config = create_database_config(
        "tls", connection_type, "localhost", 5432, "db", "user", "${TEST_DB_PASSWORD}",
        ssl_mode=ssl_mode,
    )
    save_database_config(config, str(tmp_path))
    monkeypatch.setenv("TEST_DB_PASSWORD", "resolved-secret")

    options = get_spark_database_options("tls", str(tmp_path))
    assert options["sslmode"] == ssl_mode
    assert "ssl_mode" not in options


@pytest.mark.parametrize("connection_type", ["postgres", "mysql", "custom"])
def test_connection_params_reach_spark_options(connection_type, tmp_path):
    config = create_database_config(
        "params", connection_type, "localhost", 5432, "db", "user", "",
        ApplicationName="analytics job", connectTimeout=12, readOnly=True,
        optionalSetting=None, fetchsize="2000", batchsize="3000",
    )
    save_database_config(config, str(tmp_path))

    options = get_spark_database_options("params", str(tmp_path))
    assert options["ApplicationName"] == "analytics job"
    assert options["connectTimeout"] == "12"
    assert options["readOnly"] == "true"
    assert options["timeout"] == "30"
    assert options["pool_size"] == "5"
    assert options["fetchsize"] == "2000"
    assert options["batchsize"] == "3000"
    assert "optionalSetting" not in options
    assert "ssl_mode" not in options
    assert "sslmode" not in options


@pytest.mark.parametrize(
    ("spark_tls", "connection_tls"),
    [
        ({"sslmode": "prefer"}, {"ssl_mode": "require"}),
        ({"sslmode": "verify-full"}, {"ssl_mode": "disable"}),
        ({"sslmode": "verify-full"}, {"SSLMODE": "disable"}),
        ({"SSLMODE": "verify-full"}, {"ssl_mode": "prefer"}),
    ],
    ids=["weaker-spark-option", "downgrade-ssl-mode", "downgrade-case-variant", "spark-case-variant"],
)
def test_tls_modes_that_differ_across_sections_raise(tmp_path, spark_tls, connection_tls):
    config = create_database_config("tls", "postgres", "localhost", 5432, "db", "user", "")
    config["spark_options"].update(spark_tls)
    config["connection_params"].update(connection_tls)
    save_database_config(config, str(tmp_path))

    with pytest.raises(ValueError, match="Conflicting ssl_mode and sslmode"):
        get_spark_database_options("tls", str(tmp_path))


def test_matching_tls_mode_in_both_sections_is_one_request(tmp_path):
    config = create_database_config(
        "tls", "postgres", "localhost", 5432, "db", "user", "", ssl_mode="verify-full",
    )
    config["spark_options"]["SSLMODE"] = "verify-full"
    save_database_config(config, str(tmp_path))

    options = get_spark_database_options("tls", str(tmp_path))

    assert options["sslmode"] == "verify-full"
    assert [key for key in options if key.lower() in ("sslmode", "ssl_mode")] == ["sslmode"]


@pytest.mark.parametrize("spark_key", ["sslmode", "SSLMODE", "sslMode", "ssl_mode"])
def test_spark_option_tls_alias_reaches_driver_as_sslmode(tmp_path, spark_key):
    config = create_database_config("tls", "postgres", "localhost", 5432, "db", "user", "")
    config["spark_options"][spark_key] = "verify-full"
    save_database_config(config, str(tmp_path))

    options = get_spark_database_options("tls", str(tmp_path))

    assert options["sslmode"] == "verify-full"
    assert [key for key in options if key.lower() in ("sslmode", "ssl_mode")] == ["sslmode"]


@pytest.mark.parametrize("alias", ["SSLMODE", "sslMode", "ssl_mode"])
def test_null_sslmode_does_not_erase_a_spark_option_tls_alias(tmp_path, alias):
    config = create_database_config("tls", "postgres", "localhost", 5432, "db", "user", "")
    config["spark_options"][alias] = "verify-full"
    config["spark_options"]["sslmode"] = None
    save_database_config(config, str(tmp_path))

    options = get_spark_database_options("tls", str(tmp_path))

    assert options["sslmode"] == "verify-full"


def test_null_sslmode_before_a_spark_option_tls_alias_is_replaced(tmp_path):
    config = create_database_config("tls", "postgres", "localhost", 5432, "db", "user", "")
    config["spark_options"]["sslmode"] = None
    config["spark_options"]["SSLMODE"] = "verify-full"
    save_database_config(config, str(tmp_path))

    assert get_spark_database_options("tls", str(tmp_path))["sslmode"] == "verify-full"


def test_ipv6_host_is_preserved():
    config = create_database_config("a", "postgres", "[::1]", 5432, "db", "user", "")

    assert config["jdbc_url"] == "jdbc:postgresql://[::1]:5432/db"


@pytest.mark.parametrize(
    ("connection_type", "expected_url"),
    [
        ("postgres", "jdbc:postgresql://[::1]:5432/my%20db%2F%2B%3F%23"),
        ("mysql", "jdbc:mysql://[::1]:5432/my%20db%2F%2B%3F%23"),
        ("oracle", "jdbc:oracle:thin:@[::1]:5432:my%20db%2F%2B%3F%23"),
        ("sqlserver", "jdbc:sqlserver://[::1]:5432;databaseName=my%20db%2F%2B%3F%23"),
        ("custom", "jdbc:custom://[::1]:5432/my%20db%2F%2B%3F%23"),
    ],
)
def test_database_segment_encoding_is_consistent(connection_type, expected_url):
    config = create_database_config(
        "path", connection_type, "[::1]", 5432, "my db/+?#", "user", "",
    )

    assert config["jdbc_url"] == expected_url


# --- #1476 re-review: host injection, core-key precedence, non-postgres
# ssl_mode, and no secret echo (reviewer drop-in set) ---

@pytest.mark.parametrize("host", [
    "evil.example/x?socketFactory=org.example.Evil&socketFactoryArg=http://a/b#",
    "db.example.com:5432/other?sslmode=disable&",
    "user:pw@db.example.com",
    "db.example.com ; x",
])
def test_host_cannot_inject_jdbc_url_components(host):
    with pytest.raises(ValueError):
        create_database_config("h", "postgres", host, 5432, "db", "u", "p")


def test_bare_ipv6_host_is_bracketed_or_rejected():
    try:
        url = create_database_config("h", "postgres", "::1", 5432, "db", "u", "p")["jdbc_url"]
    except ValueError:
        return
    assert url == "jdbc:postgresql://[::1]:5432/db"


def test_connection_params_cannot_replace_core_spark_options(tmp_path):
    config = create_database_config(
        "ov", "postgres", "h", 1, "db", "u", "",
        url="jdbc:postgresql://other/db", driver="x.Other", user="root",
    )
    save_database_config(config, str(tmp_path))
    options = get_spark_database_options("ov", str(tmp_path))
    assert (options["url"], options["driver"], options["user"]) == (
        "jdbc:postgresql://h:1/db", "org.postgresql.Driver", "u")


@pytest.mark.parametrize("connection_type", ["mysql", "sqlserver", "oracle"])
def test_ssl_mode_is_rejected_for_non_postgres_types(connection_type, tmp_path, monkeypatch):
    config = create_database_config(
        "tls", connection_type, "h", 1, "db", "u", "${RV_TLS_PW}", ssl_mode="require")
    save_database_config(config, str(tmp_path))
    monkeypatch.setenv("RV_TLS_PW", "x")
    # Forwarding the literal key would be ignored by these drivers, so it must fail closed.
    with pytest.raises(ValueError, match="ssl_mode is not supported"):
        get_spark_database_options("tls", str(tmp_path))


def test_invalid_reference_error_does_not_echo_the_value(tmp_path):
    (tmp_path / "database_legacy.json").write_text(json.dumps({"password": "${RvSentinel-7}"}))
    with pytest.raises(ValueError) as excinfo:
        load_database_config("legacy", str(tmp_path))
    assert "RvSentinel-7" not in str(excinfo.value)


def test_create_database_config_keeps_the_4_0_0_public_signature():
    # The minor-release API contract compares this exact string (#1476).
    assert str(inspect.signature(create_database_config)) == (
        "(name: str, connection_type: str, host: str, port: int, database: str, "
        "username: str, password: str, **kwargs) -> Dict[str, Any]"
    )


def test_digit_string_port_is_still_accepted_at_runtime():
    config = create_database_config("db", "postgres", "localhost", "5432", "d", "u", "p")
    assert config["jdbc_url"] == "jdbc:postgresql://localhost:5432/d"
