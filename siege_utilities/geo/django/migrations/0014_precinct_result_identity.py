"""Enforce one result per precinct, election, candidate, and source.

PostgreSQL does not allow UNIQUE NOT VALID / VALIDATE CONSTRAINT. Build
and validate the unique index concurrently, then attach it in a separate
ALTER TABLE to avoid scanning the table under ACCESS EXCLUSIVE. This is
the UNIQUE equivalent of the staged CHECK validation in migration 0013.
https://www.postgresql.org/docs/17/sql-altertable.html

This migration requires PostgreSQL (the siege_geo app uses PostGIS).
Existing duplicate keys abort index creation without discarding data:
operators must reconcile those rows before retrying. A retry drops any
unattached index left by an interrupted or failed build. Reversal drops
the constraint and its owned index, leaving result rows unchanged.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("siege_geo", "0013_vtd_geoid_charclass"),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP INDEX CONCURRENTLY IF EXISTS "precinct_result_identity_idx"',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX CONCURRENTLY "precinct_result_identity_idx"
                ON "siege_geo_precinctelectionresult"
                ("state_fips", "election_year", "precinct_id", "office",
                 "party", "candidate_name", "data_source")
            """,
            reverse_sql=('DROP INDEX CONCURRENTLY IF EXISTS "precinct_result_identity_idx"'),
        ),
        migrations.RunSQL(
            sql="""
                ALTER TABLE "siege_geo_precinctelectionresult"
                ADD CONSTRAINT "precinct_result_identity_uniq"
                UNIQUE USING INDEX "precinct_result_identity_idx"
            """,
            reverse_sql=(
                'ALTER TABLE "siege_geo_precinctelectionresult" '
                'DROP CONSTRAINT IF EXISTS "precinct_result_identity_uniq"'
            ),
            state_operations=[
                migrations.AddConstraint(
                    model_name="precinctelectionresult",
                    constraint=models.UniqueConstraint(
                        fields=[
                            "state_fips",
                            "election_year",
                            "precinct_id",
                            "office",
                            "party",
                            "candidate_name",
                            "data_source",
                        ],
                        name="precinct_result_identity_uniq",
                    ),
                ),
            ],
        ),
    ]
