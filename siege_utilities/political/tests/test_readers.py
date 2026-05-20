"""
Cross-backend reader sanity tests.

These verify the SQL the readers generate without needing a live
PostgreSQL connection. A stub engine captures the query + params.
Full DB integration is covered by a separate env-var-gated test suite.
"""

import pytest

from siege_utilities.political import readers


class _StubEngine:
    """Minimal engine stub that captures the SQL + params passed to query()."""

    def __init__(self):
        self.calls: list[tuple[str, list]] = []

    def query(self, sql, params=None, **kwargs):
        self.calls.append((sql, list(params or [])))
        return ("SQL", sql, list(params or []))


def test_seats_no_filters_orders_by_natural_key():
    eng = _StubEngine()
    readers.seats(eng)
    sql, params = eng.calls[0]
    assert 'political."seats"' in sql
    assert "ORDER BY office_code, state_code, district_label, senate_class" in sql
    assert params == []


def test_seats_filters_compose_parameterized_where():
    eng = _StubEngine()
    readers.seats(eng, office_code="US_HOUSE", state_code="TX", senate_class=None)
    sql, params = eng.calls[0]
    assert "WHERE office_code = %s AND state_code = %s" in sql
    assert params == ["US_HOUSE", "TX"]


def test_seats_rejects_senate_class_cast():
    eng = _StubEngine()
    readers.seats(eng, senate_class=2)
    sql, params = eng.calls[0]
    assert "senate_class = %s" in sql
    assert params == [2]
    assert isinstance(params[0], int)


def test_office_terms_current_only_filter():
    eng = _StubEngine()
    readers.office_terms(eng, current_only=True)
    sql, _ = eng.calls[0]
    assert "term_end IS NULL" in sql


def test_office_terms_as_of_date_filter():
    eng = _StubEngine()
    readers.office_terms(eng, as_of_date="2024-01-03")
    sql, params = eng.calls[0]
    assert "term_start <= %s AND (term_end IS NULL OR term_end > %s)" in sql
    assert params == ["2024-01-03", "2024-01-03"]


def test_congressional_terms_filters():
    eng = _StubEngine()
    readers.congressional_terms(eng, congress_number=118, is_presidential=False)
    sql, params = eng.calls[0]
    assert "congress_number = %s" in sql
    assert "is_presidential = %s" in sql
    assert params == [118, False]


def test_redistricting_plans_active_only():
    eng = _StubEngine()
    readers.redistricting_plans(eng, jurisdiction_code="US-TX", active_only=True)
    sql, params = eng.calls[0]
    assert "jurisdiction_code = %s" in sql
    assert "effective_to_date IS NULL" in sql
    assert params == ["US-TX"]


def test_plan_district_assignments_by_seat():
    eng = _StubEngine()
    readers.plan_district_assignments(eng, seat_id="00000000-0000-0000-0000-000000000001")
    sql, params = eng.calls[0]
    assert "seat_id = %s" in sql
    assert len(params) == 1


def test_state_election_calendars_by_year():
    eng = _StubEngine()
    readers.state_election_calendars(eng, state_code="TX", election_year=2024)
    sql, params = eng.calls[0]
    assert "state_code = %s" in sql
    assert "election_year = %s" in sql
    assert params == ["TX", 2024]


def test_qualified_rejects_unsafe_identifier():
    # Even though we only feed fixed strings internally, the quoter
    # should reject anything that could inject SQL.
    with pytest.raises(ValueError, match="unsafe identifier"):
        readers._quote_ident("seats; DROP TABLE x; --")
    with pytest.raises(ValueError, match="unsafe identifier"):
        readers._quote_ident("")


def test_readers_exported_from_package():
    from siege_utilities.political import readers as pol_readers
    for fn in ("seats", "office_terms", "congressional_terms",
               "redistricting_plans", "plan_district_assignments",
               "state_election_calendars"):
        assert hasattr(pol_readers, fn)
