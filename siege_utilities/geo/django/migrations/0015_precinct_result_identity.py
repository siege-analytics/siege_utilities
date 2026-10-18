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
the constraint, its owned index, and the added identity columns.

The pre-migration loader only stored general elections and no real House
columns, so legacy rows receive G and an empty district. Recover known
party letters from display labels; keep unmapped legacy labels verbatim
because the original VEST letter cannot be reconstructed from OTHER.
Reloading from the source replaces that legacy identity with the raw code.
Column creation and backfill are retryable if concurrent index creation
fails. No result rows are discarded or combined.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("siege_geo", "0014_district_geoid_charclass"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                'ALTER TABLE "siege_geo_precinctelectionresult" '
                'ADD COLUMN IF NOT EXISTS "election_type" varchar(1) NOT NULL DEFAULT \'G\'',
                'ALTER TABLE "siege_geo_precinctelectionresult" '
                'ALTER COLUMN "election_type" DROP DEFAULT',
                'ALTER TABLE "siege_geo_precinctelectionresult" '
                'ADD COLUMN IF NOT EXISTS "district" varchar(2) NOT NULL DEFAULT \'\'',
                'ALTER TABLE "siege_geo_precinctelectionresult" '
                'ALTER COLUMN "district" DROP DEFAULT',
                'ALTER TABLE "siege_geo_precinctelectionresult" '
                'ADD COLUMN IF NOT EXISTS "party_code" varchar(50) NOT NULL DEFAULT \'\'',
                'ALTER TABLE "siege_geo_precinctelectionresult" '
                'ALTER COLUMN "party_code" DROP DEFAULT',
            ],
            reverse_sql=[
                'ALTER TABLE "siege_geo_precinctelectionresult" DROP COLUMN IF EXISTS "party_code"',
                'ALTER TABLE "siege_geo_precinctelectionresult" DROP COLUMN IF EXISTS "district"',
                'ALTER TABLE "siege_geo_precinctelectionresult" DROP COLUMN IF EXISTS "election_type"',
            ],
            state_operations=[
                migrations.AddField(
                    model_name="precinctelectionresult",
                    name="election_type",
                    field=models.CharField(
                        max_length=1, default="G",
                        help_text="VEST election type (G general, S special, R runoff, C recount, P primary)",
                    ),
                ),
                migrations.AddField(
                    model_name="precinctelectionresult",
                    name="district",
                    field=models.CharField(
                        max_length=2, blank=True, default="",
                        help_text="VEST House district (two digits or AL); blank for statewide offices",
                    ),
                ),
                migrations.AddField(
                    model_name="precinctelectionresult",
                    name="party_code",
                    field=models.CharField(
                        max_length=50, blank=True, default="",
                        help_text="Raw VEST party letter; legacy rows retain unmapped party labels",
                    ),
                ),
            ],
        ),
        migrations.RunSQL(
            sql="""
                UPDATE "siege_geo_precinctelectionresult"
                SET "party_code" = CASE "party"
                    WHEN 'DEM' THEN 'D' WHEN 'REP' THEN 'R' WHEN 'LIB' THEN 'L'
                    WHEN 'GRN' THEN 'G' WHEN 'IND' THEN 'I' ELSE "party" END
                WHERE "party_code" = ''
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql='DROP INDEX CONCURRENTLY IF EXISTS "precinct_result_identity_idx"',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX CONCURRENTLY "precinct_result_identity_idx"
                ON "siege_geo_precinctelectionresult"
                ("state_fips", "election_year", "election_type", "precinct_id",
                 "office", "district", "party_code", "candidate_name", "data_source")
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
                            "election_type",
                            "precinct_id",
                            "office",
                            "district",
                            "party_code",
                            "candidate_name",
                            "data_source",
                        ],
                        name="precinct_result_identity_uniq",
                    ),
                ),
            ],
        ),
    ]
