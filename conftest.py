"""Fail closed when a live Django database test is missing the PostGIS marker.

Both the generic matrix and the live service lane collect the whole test tree.
The former excludes ``postgis`` tests; the latter selects them. A new test
requesting a Django DB fixture without the marker must fail collection, not
silently run only in the wrong lane or disappear from the service lane.
"""

import pytest


_DB_FIXTURES = frozenset({"db", "transactional_db"})


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """Require explicit live-service routing for collected Django DB tests."""
    missing = [
        item.nodeid
        for item in items
        if (
            _DB_FIXTURES.intersection(item.fixturenames)
            # pytest-django injects django_db_blocker into *every* test's
            # fixture closure; only an explicit request is a DB contract.
            or "django_db_blocker" in item._fixtureinfo.argnames
            or item.get_closest_marker("django_db") is not None
        )
        and item.get_closest_marker("postgis") is None
    ]
    if missing:
        raise pytest.UsageError(
            "Django DB tests require @pytest.mark.postgis and a live "
            "PostGIS lane; unmarked tests:\n" + "\n".join(missing)
        )
