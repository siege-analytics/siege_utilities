#!/bin/bash
# Set up PostGIS test database for siege_utilities Django ORM tests.
#
# Usage:
#   sudo -u postgres bash scripts/setup_test_db.sh
#
# Or with a specific user:
#   PGUSER=myuser PGPASSWORD=mypass bash scripts/setup_test_db.sh

set -e

DB_NAME="${SIEGE_TEST_DB_NAME:-siege_geo}"

echo "Creating database: $DB_NAME"
psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "Database $DB_NAME already exists"

echo "Enabling PostGIS extension"
psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS postgis;"

echo "Verifying PostGIS"
psql -d "$DB_NAME" -c "SELECT PostGIS_Version();"

echo ""
echo "Done. To run Django ORM tests:"
echo "  export SIEGE_TEST_DB_PASSWORD=postgres"
echo "  pytest tests/test_django_temporal_models_orm.py -v"
