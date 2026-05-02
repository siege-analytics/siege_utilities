"""
Cross-backend readers for siege_utilities.political tables.

PostgreSQL is the canonical write/DDL home for political schema (raw
SQL migrations under migrations/). READ access is available through
any :class:`~siege_utilities.data.dataframe_engine.DataFrameEngine`
backend by routing the query through ``engine.query(sql)``:

- ``PostGISEngine`` — direct psycopg/SQLAlchemy query against the PG DB
- ``SparkEngine`` — JDBC read via PostgreSQL JDBC driver; Sedona for
  spatial ops on PG-sourced rows
- ``DuckDBEngine`` — ``postgres_scanner`` extension (ATTACH plus query)
- ``PandasEngine`` — falls back to SQLAlchemy + pandas.read_sql

**Parameter binding:** Readers pass ``params=`` to ``engine.query()``.
This works correctly on ``PostGISEngine`` (psycopg) and ``PandasEngine``
(SQLAlchemy). ``SparkEngine`` and ``DuckDBEngine`` currently ignore the
``params`` kwarg — callers targeting those backends must apply filters
through the engine's own mechanisms rather than relying on these helpers.

Callers hand an already-configured engine to these readers; engine
construction (connection strings, Spark sessions, DuckDB ATTACH) stays
the caller's responsibility.

See ``siege_utilities/political/__init__.py`` for the companion write-
side helper ``schema_migrations_dir()``.
"""

from __future__ import annotations

from typing import Any, Optional


_POLITICAL_SCHEMA = "political"


def _quote_ident(name: str) -> str:
    """Very conservative identifier quoter. Rejects unsafe characters."""
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"unsafe identifier: {name!r}")
    return f'"{name}"'


def _qualified(table: str) -> str:
    return f"{_POLITICAL_SCHEMA}.{_quote_ident(table)}"


# ----------------------------------------------------------------------
# seats
# ----------------------------------------------------------------------

def seats(
    engine: Any,
    *,
    office_code: Optional[str] = None,
    state_code: Optional[str] = None,
    senate_class: Optional[int] = None,
    jurisdiction_code: Optional[str] = None,
) -> Any:
    """Read ``political.seats`` via the given engine.

    Optional filters build a parameterized WHERE clause. Returns
    whatever the engine's ``query`` method returns (pandas/geopandas
    DataFrame, Spark DataFrame, DuckDB relation).
    """
    clauses = []
    params: list[Any] = []
    if office_code is not None:
        clauses.append("office_code = %s")
        params.append(office_code)
    if state_code is not None:
        clauses.append("state_code = %s")
        params.append(state_code)
    if senate_class is not None:
        clauses.append("senate_class = %s")
        params.append(int(senate_class))
    if jurisdiction_code is not None:
        clauses.append("jurisdiction_code = %s")
        params.append(jurisdiction_code)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        f"SELECT * FROM {_qualified('seats')} {where}"
        " ORDER BY office_code, state_code, district_label, senate_class, id"
    )
    return engine.query(sql, params=params)


# ----------------------------------------------------------------------
# office_terms
# ----------------------------------------------------------------------

def office_terms(
    engine: Any,
    *,
    seat_id: Optional[str] = None,
    incumbent_agent_id: Optional[str] = None,
    current_only: bool = False,
    as_of_date: Optional[str] = None,
) -> Any:
    """Read ``political.office_terms``.

    Args:
        engine: DataFrameEngine instance.
        seat_id: Filter to a specific Seat.
        incumbent_agent_id: Filter to a specific incumbent.
        current_only: Only rows where ``term_end IS NULL``.
        as_of_date: ISO date string; returns rows where term was in
            effect on that date (``term_start <= as_of AND
            (term_end IS NULL OR term_end > as_of)``).
    """
    clauses = []
    params: list[Any] = []
    if seat_id is not None:
        clauses.append("seat_id = %s")
        params.append(seat_id)
    if incumbent_agent_id is not None:
        clauses.append("incumbent_agent_id = %s")
        params.append(incumbent_agent_id)
    if current_only:
        clauses.append("term_end IS NULL")
    if as_of_date is not None:
        clauses.append("(term_start <= %s AND (term_end IS NULL OR term_end > %s))")
        params.extend([as_of_date, as_of_date])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM {_qualified('office_terms')} {where} ORDER BY term_start DESC, id"
    return engine.query(sql, params=params)


# ----------------------------------------------------------------------
# congressional_terms
# ----------------------------------------------------------------------

def congressional_terms(
    engine: Any,
    *,
    congress_number: Optional[int] = None,
    election_year: Optional[int] = None,
    is_presidential: Optional[bool] = None,
) -> Any:
    """Read ``political.congressional_terms``."""
    clauses = []
    params: list[Any] = []
    if congress_number is not None:
        clauses.append("congress_number = %s")
        params.append(int(congress_number))
    if election_year is not None:
        clauses.append("election_year = %s")
        params.append(int(election_year))
    if is_presidential is not None:
        clauses.append("is_presidential = %s")
        params.append(bool(is_presidential))

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        f"SELECT * FROM {_qualified('congressional_terms')} {where}"
        " ORDER BY congress_number DESC, office_term_id"
    )
    return engine.query(sql, params=params)


# ----------------------------------------------------------------------
# redistricting_plans + plan_district_assignments
# ----------------------------------------------------------------------

def redistricting_plans(
    engine: Any,
    *,
    jurisdiction_code: Optional[str] = None,
    plan_type: Optional[str] = None,
    active_only: bool = False,
) -> Any:
    """Read ``political.redistricting_plans``."""
    clauses = []
    params: list[Any] = []
    if jurisdiction_code is not None:
        clauses.append("jurisdiction_code = %s")
        params.append(jurisdiction_code)
    if plan_type is not None:
        clauses.append("plan_type = %s")
        params.append(plan_type)
    if active_only:
        clauses.append("effective_to_date IS NULL")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        f"SELECT * FROM {_qualified('redistricting_plans')} {where}"
        " ORDER BY effective_from_date DESC, id"
    )
    return engine.query(sql, params=params)


def plan_district_assignments(
    engine: Any,
    *,
    plan_id: Optional[str] = None,
    seat_id: Optional[str] = None,
) -> Any:
    """Read ``political.plan_district_assignments``."""
    clauses = []
    params: list[Any] = []
    if plan_id is not None:
        clauses.append("plan_id = %s")
        params.append(plan_id)
    if seat_id is not None:
        clauses.append("seat_id = %s")
        params.append(seat_id)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        f"SELECT * FROM {_qualified('plan_district_assignments')} {where}"
        " ORDER BY plan_id, seat_id, id"
    )
    return engine.query(sql, params=params)


# ----------------------------------------------------------------------
# state_election_calendars
# ----------------------------------------------------------------------

def state_election_calendars(
    engine: Any,
    *,
    state_code: Optional[str] = None,
    congress_number: Optional[int] = None,
    election_year: Optional[int] = None,
) -> Any:
    """Read ``political.state_election_calendars``."""
    clauses = []
    params: list[Any] = []
    if state_code is not None:
        clauses.append("state_code = %s")
        params.append(state_code)
    if congress_number is not None:
        clauses.append("congress_number = %s")
        params.append(int(congress_number))
    if election_year is not None:
        clauses.append("election_year = %s")
        params.append(int(election_year))

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        f"SELECT * FROM {_qualified('state_election_calendars')} {where}"
        " ORDER BY general_date DESC, id"
    )
    return engine.query(sql, params=params)


__all__ = [
    "seats",
    "office_terms",
    "congressional_terms",
    "redistricting_plans",
    "plan_district_assignments",
    "state_election_calendars",
]
