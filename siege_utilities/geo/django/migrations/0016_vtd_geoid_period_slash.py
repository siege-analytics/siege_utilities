"""Accept periods and slashes in the six-character VTDST tail of VTD GEOIDs.

Census 2020 PL TIGER/Line Technical Documentation, section 4.19 (p. 4-48)
and Appendix U-1/U-2 (pp. 145-146), defines six-character VTDST20 and
eleven-character GEOID20 = STATEFP20 + COUNTYFP20 + VTDST20:
https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2020pl/TGRSHP2020PL_TechDoc.pdf
The observed VTDST alphabet includes ASCII digits, both letter cases,
periods, slashes, and hyphens. The read-only warehouse check documented at
https://github.com/siege-analytics/siege_utilities/issues/1399#issuecomment-6134787768
found 1,566 of 158,444 TIGER-loaded VTD GEOIDs rejected by 0013's narrower
alphabet. Examples include 010130012.2, 120170100.1, 05081000L/C, and
05081000R/R. The five-character FIPS prefix remains digits-only.

Use PostgreSQL NOT VALID followed by a separate VALIDATE CONSTRAINT to
avoid scanning the populated table under ACCESS EXCLUSIVE. atomic=False
releases the swap's DDL lock before validation takes SHARE UPDATE EXCLUSIVE.
Each swap is one ALTER TABLE statement, so writes never see an unconstrained
table. Drop/re-add also permits retry after an interrupted validation.
Django state operations mirror the SQL constraint replacement.

Reversal restores AND validates 0013's narrower alphabet. It fails if rows
containing periods or slashes remain; remove or correct incompatible data
before retrying. A failed validation leaves the restored constraint NOT
VALID, but still enforced for new writes. This migration cannot repair a
database whose migration run already fails at 0011 or 0013.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("siege_geo", "0015_precinct_result_identity"),
    ]

    operations = [
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=(
                'ALTER TABLE "siege_geo_vtd" '
                'VALIDATE CONSTRAINT "vtd_geoid_format"'
            ),
        ),
        migrations.RunSQL(
            sql=r"""
                ALTER TABLE "siege_geo_vtd"
                DROP CONSTRAINT IF EXISTS "vtd_geoid_format",
                ADD CONSTRAINT "vtd_geoid_format"
                CHECK ("geoid" ~ '^\d{5}[0-9A-Za-z./-]{6}$') NOT VALID
            """,
            reverse_sql=r"""
                ALTER TABLE "siege_geo_vtd"
                DROP CONSTRAINT IF EXISTS "vtd_geoid_format",
                ADD CONSTRAINT "vtd_geoid_format"
                CHECK ("geoid" ~ '^\d{5}[0-9A-Za-z-]{6}$') NOT VALID
            """,
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="vtd",
                    name="vtd_geoid_format",
                ),
                migrations.AddConstraint(
                    model_name="vtd",
                    constraint=models.CheckConstraint(
                        condition=models.Q(geoid__regex=r"^\d{5}[0-9A-Za-z./-]{6}$"),
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
