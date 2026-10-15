"""Accept the observed session-embedded CD112 GEOIDs.

The warehouse verification records 441 seven-digit CD112 codes among 6,173
congressional district rows, including 0111201, 4811227, 0611253 and 0211200:
https://github.com/siege-analytics/siege_utilities/issues/1522#issuecomment-6184641103
Only the observed STATEFP + 112 + numeric CD form extends the existing
four-character alphabet. SLDU and SLDL already accept every observed row.
The population service canonicalizes incoming session-embedded codes before
identity lookup and parsing, avoiding duplicate identities and district 11.

Swap under one ALTER TABLE, then validate in a separate transaction so the
scan does not hold ACCESS EXCLUSIVE. Reversal restores and validates 0014's
four-character CHECK; incompatible rows must be reconciled before reversal.
An interrupted validation can be retried without an unconstrained write gap.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("siege_geo", "0016_vtd_geoid_period_slash"),
    ]

    operations = [
        migrations.RunSQL(
            sql=migrations.RunSQL.noop,
            reverse_sql=(
                'ALTER TABLE "siege_geo_congressionaldistrict" '
                'VALIDATE CONSTRAINT "cd_geoid_format"'
            ),
        ),
        migrations.RunSQL(
            sql=r"""
                ALTER TABLE "siege_geo_congressionaldistrict"
                DROP CONSTRAINT IF EXISTS "cd_geoid_format",
                ADD CONSTRAINT "cd_geoid_format"
                CHECK ("geoid" ~ '^\d{2}([0-9A-Za-z]{2}|112[0-9]{2})$') NOT VALID
            """,
            reverse_sql=r"""
                ALTER TABLE "siege_geo_congressionaldistrict"
                DROP CONSTRAINT IF EXISTS "cd_geoid_format",
                ADD CONSTRAINT "cd_geoid_format"
                CHECK ("geoid" ~ '^\d{2}[0-9A-Za-z]{2}$') NOT VALID
            """,
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="congressionaldistrict", name="cd_geoid_format",
                ),
                migrations.AddConstraint(
                    model_name="congressionaldistrict",
                    constraint=models.CheckConstraint(
                        condition=models.Q(geoid__regex=r"^\d{2}([0-9A-Za-z]{2}|112[0-9]{2})$"),
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
    ]
