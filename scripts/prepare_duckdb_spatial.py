#!/usr/bin/env python3
"""Provision the real DuckDB spatial extension before integration tests.

A cold runner must not depend on another test installing the extension first.
Failures here remain blocking; no mock or skip replaces spatial integration.
"""

import duckdb


def main() -> None:
    connection = duckdb.connect()
    try:
        connection.execute("INSTALL spatial")
        connection.execute("LOAD spatial")
        point = connection.execute("SELECT ST_AsText(ST_Point(1, 2))").fetchone()
        assert point == ("POINT (1 2)",), point
    finally:
        connection.close()


if __name__ == "__main__":
    main()
