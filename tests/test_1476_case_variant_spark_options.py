"""Case-variant TLS and core option keys, and null optional config sections (#1476).

Spark matches JDBC option keys case-insensitively but passes the surviving key to
the driver in its own case, so a case variant of ``sslmode`` or of a core key
must neither override the requested TLS mode nor replace the configured
connection.
"""
import json

import pytest

from siege_utilities.config.databases import (
    create_database_config,
    get_spark_database_options,
    save_database_config,
)

CORE = ("url", "driver", "user", "password")


@pytest.mark.parametrize("extra", [
    {"SSLMODE": "disable"},
    {"sslMode": "VERIFY_IDENTITY"},
    {"SSL_MODE": "disable"},
])
def test_case_variant_tls_alias_cannot_override_ssl_mode(extra, tmp_path):
    config = create_database_config(
        "tls", "postgres", "h", 1, "db", "u", "", ssl_mode="verify-full", **extra)
    save_database_config(config, str(tmp_path))
    with pytest.raises(ValueError, match="Conflicting ssl_mode and sslmode"):
        get_spark_database_options("tls", str(tmp_path))


@pytest.mark.parametrize("extra", [{"SSL_MODE": "verify-full"}, {"SslMode": "verify-full"}])
def test_case_variant_tls_alias_reaches_pgjdbc_as_sslmode(extra, tmp_path):
    config = create_database_config("tls", "postgres", "h", 1, "db", "u", "", **extra)
    save_database_config(config, str(tmp_path))
    options = get_spark_database_options("tls", str(tmp_path))
    assert {k: v for k, v in options.items() if "ssl" in k.lower()} == {"sslmode": "verify-full"}


@pytest.mark.parametrize("extra", [
    {"URL": "jdbc:postgresql://other/db"},
    {"Driver": "x.Other"},
    {"USER": "root"},
    {"Password": "other"},
])
def test_case_variant_core_keys_cannot_replace_core_spark_options(extra, tmp_path):
    config = create_database_config("ov", "postgres", "h", 1, "db", "u", "", **extra)
    save_database_config(config, str(tmp_path))
    options = get_spark_database_options("ov", str(tmp_path))
    assert sorted(k for k in options if k.lower() in CORE) == sorted(CORE)
    assert (options["url"], options["driver"], options["user"]) == (
        "jdbc:postgresql://h:1/db", "org.postgresql.Driver", "u")


def test_option_keys_differing_only_by_case_raise(tmp_path):
    config = create_database_config("dup", "mysql", "h", 1, "db", "u", "", useSSL="true", usessl="false")
    save_database_config(config, str(tmp_path))
    with pytest.raises(ValueError, match="differ only by case"):
        get_spark_database_options("dup", str(tmp_path))


@pytest.mark.parametrize("field", ["connection_params", "connection_type", "spark_options"])
def test_null_optional_sections_in_a_hand_written_file_are_tolerated(field, tmp_path):
    body = {"jdbc_url": "jdbc:postgresql://h:1/db", "jdbc_driver": "org.postgresql.Driver",
            "username": "u", "password": "", field: None}
    (tmp_path / "database_legacy.json").write_text(json.dumps(body))
    assert get_spark_database_options("legacy", str(tmp_path))["url"] == "jdbc:postgresql://h:1/db"
