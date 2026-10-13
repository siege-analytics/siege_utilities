"""Allow TIGER congressional and state legislative district GEOIDs.

Census 2025 TIGER/Line Technical Documentation, sections 4.5 and 4.19,
and Appendix H-1/H-2/H-3 (PDF pp. 134-136), defines GEOID as the two-digit
STATEFP plus a two-character CD code or three-character SLD code:
https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2025/TGRSHP2025_TechDoc.pdf

Census 2025 Geographic Reference Files Legal Values, PDF p. 9, lists
CDCURFP codes including ZZ and permits alphanumeric characters plus dash
for SLDUST/SLDLST, including ZZZ (unassigned districts):
https://www2.census.gov/geo/pdfs/maps-data/data/2025GRF_legal_values.pdf
Thus hyphens belong in SLD codes, but not CD codes. Uppercase follows the
published district-code convention; these references do not explicitly
state a letter-case restriction for SLD codes. These checks enforce the
GEOID shape, not the set of district numbers assigned in a given vintage.

Each constraint swap is one ALTER TABLE with NOT VALID. A separate
VALIDATE CONSTRAINT scans existing rows after releasing ACCESS EXCLUSIVE;
atomic=False keeps the swap lock out of the validation transaction.
State operations mirror every replacement, and drop/re-add permits retry
if validation was interrupted.

Reversal restores and separately validates the digits-only constraints.
Remove incompatible district rows before reversing; otherwise validation
fails, leaving the restored constraint NOT VALID but enforced on new writes.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("siege_geo", "0013_vtd_geoid_charclass"),
    ]

    operations = [
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=(
                'ALTER TABLE "siege_geo_congressionaldistrict" '
                'VALIDATE CONSTRAINT "cd_geoid_4_digits"'
            ),
        ),
        migrations.RunSQL(
            sql=r"""
                ALTER TABLE "siege_geo_congressionaldistrict"
                DROP CONSTRAINT IF EXISTS "cd_geoid_4_digits",
                DROP CONSTRAINT IF EXISTS "cd_geoid_format",
                ADD CONSTRAINT "cd_geoid_format"
                CHECK ("geoid" ~ '^\d{2}[0-9A-Z]{2}$') NOT VALID
            """,
            reverse_sql=r"""
                ALTER TABLE "siege_geo_congressionaldistrict"
                DROP CONSTRAINT IF EXISTS "cd_geoid_format",
                DROP CONSTRAINT IF EXISTS "cd_geoid_4_digits",
                ADD CONSTRAINT "cd_geoid_4_digits"
                CHECK ("geoid" ~ '^\d{4}$') NOT VALID
            """,
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="congressionaldistrict",
                    name="cd_geoid_4_digits",
                ),
                migrations.AddConstraint(
                    model_name="congressionaldistrict",
                    constraint=models.CheckConstraint(
                        condition=models.Q(geoid__regex=r"^\d{2}[0-9A-Z]{2}$"),
                        name="cd_geoid_format",
                    ),
                ),
            ],
        ),
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "siege_geo_congressionaldistrict" '
                'VALIDATE CONSTRAINT "cd_geoid_format"'
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=(
                'ALTER TABLE "siege_geo_statelegislativeupper" '
                'VALIDATE CONSTRAINT "sldu_geoid_5_digits"'
            ),
        ),
        migrations.RunSQL(
            sql=r"""
                ALTER TABLE "siege_geo_statelegislativeupper"
                DROP CONSTRAINT IF EXISTS "sldu_geoid_5_digits",
                DROP CONSTRAINT IF EXISTS "sldu_geoid_format",
                ADD CONSTRAINT "sldu_geoid_format"
                CHECK ("geoid" ~ '^\d{2}[0-9A-Z-]{3}$') NOT VALID
            """,
            reverse_sql=r"""
                ALTER TABLE "siege_geo_statelegislativeupper"
                DROP CONSTRAINT IF EXISTS "sldu_geoid_format",
                DROP CONSTRAINT IF EXISTS "sldu_geoid_5_digits",
                ADD CONSTRAINT "sldu_geoid_5_digits"
                CHECK ("geoid" ~ '^\d{5}$') NOT VALID
            """,
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="statelegislativeupper",
                    name="sldu_geoid_5_digits",
                ),
                migrations.AddConstraint(
                    model_name="statelegislativeupper",
                    constraint=models.CheckConstraint(
                        condition=models.Q(geoid__regex=r"^\d{2}[0-9A-Z-]{3}$"),
                        name="sldu_geoid_format",
                    ),
                ),
            ],
        ),
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "siege_geo_statelegislativeupper" '
                'VALIDATE CONSTRAINT "sldu_geoid_format"'
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=(
                'ALTER TABLE "siege_geo_statelegislativelower" '
                'VALIDATE CONSTRAINT "sldl_geoid_5_digits"'
            ),
        ),
        migrations.RunSQL(
            sql=r"""
                ALTER TABLE "siege_geo_statelegislativelower"
                DROP CONSTRAINT IF EXISTS "sldl_geoid_5_digits",
                DROP CONSTRAINT IF EXISTS "sldl_geoid_format",
                ADD CONSTRAINT "sldl_geoid_format"
                CHECK ("geoid" ~ '^\d{2}[0-9A-Z-]{3}$') NOT VALID
            """,
            reverse_sql=r"""
                ALTER TABLE "siege_geo_statelegislativelower"
                DROP CONSTRAINT IF EXISTS "sldl_geoid_format",
                DROP CONSTRAINT IF EXISTS "sldl_geoid_5_digits",
                ADD CONSTRAINT "sldl_geoid_5_digits"
                CHECK ("geoid" ~ '^\d{5}$') NOT VALID
            """,
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="statelegislativelower",
                    name="sldl_geoid_5_digits",
                ),
                migrations.AddConstraint(
                    model_name="statelegislativelower",
                    constraint=models.CheckConstraint(
                        condition=models.Q(geoid__regex=r"^\d{2}[0-9A-Z-]{3}$"),
                        name="sldl_geoid_format",
                    ),
                ),
            ],
        ),
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "siege_geo_statelegislativelower" '
                'VALIDATE CONSTRAINT "sldl_geoid_format"'
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
