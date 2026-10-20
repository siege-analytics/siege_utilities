import pytest
from siege_utilities.config.databases import (
    create_database_config, get_spark_database_options, save_database_config,
)

@pytest.mark.parametrize("port", [
    "5432/other?sslmode=disable&socketFactory=org.example.Evil#",
    "1;encrypt=false",
    "5432:x",
    0,
    70000,
])
def test_port_cannot_inject_jdbc_url_components(port):
    with pytest.raises(ValueError):
        create_database_config("h", "postgres", "db.example.com", port, "db", "u", "p")

@pytest.mark.parametrize("port", [5432, "5432"])
def test_valid_port_still_accepted(port):
    url = create_database_config("h", "postgres", "db.example.com", port, "db", "u", "p")["jdbc_url"]
    assert url == "jdbc:postgresql://db.example.com:5432/db"

@pytest.mark.parametrize("host", ["db:5432", "cafe.db:5432", "[db:5432]", "db.example.com\n"])
def test_host_with_port_or_trailing_newline_is_rejected(host):
    with pytest.raises(ValueError):
        create_database_config("h", "postgres", host, 5432, "db", "u", "p")

@pytest.mark.parametrize("host,expected", [
    ("::1", "[::1]"), ("[::1]", "[::1]"), ("2001:db8::1", "[2001:db8::1]"), ("[2001:db8::1]", "[2001:db8::1]"),
])
def test_real_ipv6_literals_still_accepted(host, expected):
    url = create_database_config("h", "postgres", host, 5432, "db", "u", "p")["jdbc_url"]
    assert url == f"jdbc:postgresql://{expected}:5432/db"

def test_conflicting_ssl_mode_and_sslmode_do_not_downgrade(tmp_path):
    try:
        config = create_database_config(
            "c", "postgres", "h", 1, "db", "u", "", ssl_mode="require", sslmode="disable")
        save_database_config(config, str(tmp_path))
        options = get_spark_database_options("c", str(tmp_path))
    except ValueError:
        return  # rejecting the contradiction is acceptable
    assert options["sslmode"] == "require"
