# PostGIS constraint tests

The `postgis` marker exercises migration 0014's PostgreSQL `~` CHECKs and
NOT VALID / VALIDATE operations on real PostGIS tables. The SQLite loader
tests remain part of the default suite; their Python `re` implementation
does not substitute for PostgreSQL POSIX regex coverage.

Install `siege-utilities[geo,geodjango]`, pytest-django, and system GDAL/GEOS.
Start a PostgreSQL service with PostGIS installed. Create a dedicated test
database and enable `CREATE EXTENSION postgis` as its owner (see
`scripts/setup_test_db.sh`). The test user needs CREATE on that database.
Set the existing test settings and opt in:

```bash
export SIEGE_TEST_DB_NAME=siege_geo
export SIEGE_TEST_DB_USER=postgres
export SIEGE_TEST_DB_HOST=localhost
export SIEGE_TEST_DB_PORT=5432
# Set SIEGE_TEST_DB_PASSWORD if required by the service.
export SIEGE_TEST_POSTGIS=1
python -m pytest tests/test_district_geoid_postgis.py -m postgis --no-cov -rs
```

Use `DJANGO_SETTINGS_MODULE=tests.django_project.settings` if overriding the
pytest default. Configure GDAL_LIBRARY_PATH and GEOS_LIBRARY_PATH if the
system libraries are outside Django's search path.

The test connects to SIEGE_TEST_DB_NAME directly, creates the historical
State and three district model tables in a random private schema, and
drops that schema in teardown. It never applies migrations to public or
changes the database's migration history. It checks existing-row validation,
numeric, uppercase, lowercase, mixed-case and SLD hyphen codes, invalid
GEOIDs, duplicate GEOID/vintage keys, distinct vintages, and reversible DDL
including failed reverse validation and retry. Run against a test database.

Without SIEGE_TEST_POSTGIS=1, a reachable service, or the PostGIS extension,
the tests skip with the setup command and environment variables in the
message. Once connected, DDL, permissions, and assertion errors fail the
tests rather than becoming skips.
