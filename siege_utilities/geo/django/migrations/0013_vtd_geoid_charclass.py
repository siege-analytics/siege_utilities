"""Allow TIGER voting district letters and hyphens in VTD GEOIDs.

Census 2020 PL TIGER/Line Technical Documentation, section 4.19 (p. 4-48)
and Appendix U-1/U-2 (pp. 145-146), defines six-character VTDST20 and
eleven-character GEOID20 = STATEFP20 + COUNTYFP20 + VTDST20:
https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020pl/TGRSHP2020PL_TechDoc.pdf
These sections do not specify uppercase-only codes. Accept both ASCII
letter cases rather than infer a restriction from uppercase examples.
Hyphens occur in real TIGER codes such as 010110001-1.

Use PostgreSQL NOT VALID followed by a separate VALIDATE CONSTRAINT to
avoid scanning the populated table under ACCESS EXCLUSIVE. atomic=False
releases the swap's DDL lock before validation takes SHARE UPDATE EXCLUSIVE.
Each swap is one ALTER TABLE statement, so writes never see an unconstrained
table. Drop/re-add also permits retry after an interrupted validation.
Django state operations mirror the SQL constraint replacement.

Reversal restores AND validates the digits-only constraint. It fails if
alphanumeric rows remain; remove or correct incompatible data before
retrying. A failed validation leaves the restored constraint NOT VALID,
but still enforced for new writes. This migration cannot repair a database
whose migration run already fails at 0011.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("siege_geo", "0012_bargainingunit_electionresult_nlrbcase_ulpcharge_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=(
                'ALTER TABLE "siege_geo_vtd" '
                'VALIDATE CONSTRAINT "vtd_geoid_11_digits"'
            ),
        ),
        migrations.RunSQL(
            sql=r"""
                ALTER TABLE "siege_geo_vtd"
                DROP CONSTRAINT IF EXISTS "vtd_geoid_11_digits",
                DROP CONSTRAINT IF EXISTS "vtd_geoid_format",
                ADD CONSTRAINT "vtd_geoid_format"
                CHECK ("geoid" ~ '^\d{5}[0-9A-Za-z-]{6}$') NOT VALID
            """,
            reverse_sql=r"""
                ALTER TABLE "siege_geo_vtd"
                DROP CONSTRAINT IF EXISTS "vtd_geoid_format",
                DROP CONSTRAINT IF EXISTS "vtd_geoid_11_digits",
                ADD CONSTRAINT "vtd_geoid_11_digits"
                CHECK ("geoid" ~ '^\d{11}$') NOT VALID
            """,
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="vtd",
                    name="vtd_geoid_11_digits",
                ),
                migrations.AddConstraint(
                    model_name="vtd",
                    constraint=models.CheckConstraint(
                        condition=models.Q(geoid__regex=r"^\d{5}[0-9A-Za-z-]{6}$"),
                        name="vtd_geoid_format",
                    ),
                ),
            ],
        ),
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "siege_geo_vtd" '
                'VALIDATE CONSTRAINT "vtd_geoid_format"'
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
