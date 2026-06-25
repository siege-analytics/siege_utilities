"""Fix the VTD GEOID check constraint: 8 digits -> 11 digits.

Census VTD GEOIDs are 11 characters = state FIPS (2) + county FIPS (3) +
VTDST (6). The original `vtd_geoid_8_digits` constraint (regex ^\\d{8}$)
was wrong: it assumed a 3-character VTD component and would reject every
real Census VTD GEOID. This swaps it for `vtd_geoid_11_digits` (^\\d{11}$),
matching the sibling boundary constraints (county=5, tract=11, etc.) and
the model's own `vtd_code` field (max_length=6 = the VTDST component).

Pre-author state measurement (authoring-against-state:6):
- enterprise_geo.geo_censustiger_voter_tabulation_district (electinfo
  loader table, measured by Spatial Hub 2026-06-24): 158,444 rows across
  49 states, 100% 11-char geoid, vtdst component 6 chars, ZERO 8-char
  rows. Confirms the 11-char direction conclusively.
- Consuming-path note: that loader table is NOT this Django model's
  physical table. This model binds to whatever DB the consuming app's
  Django settings configure (in the library's own test context, the
  ephemeral `test_siege_geo` DB, created empty per run). No persistent
  siege-model VTD table exists in the electinfo PostGIS. The constraint
  swap is therefore a clean swap against an empty/absent model table.
- Downstream consumers applying this migration against a populated VTD
  table: real Census VTD GEOIDs are 11-char, so any pre-existing 8-char
  rows are malformed and must be re-derived as state(2)+county(3)+VTDST(6),
  NOT zero-padded, before this AddConstraint will validate.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("siege_geo", "0010_seat_state_constraint"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="vtd",
            name="vtd_geoid_8_digits",
        ),
        migrations.AddConstraint(
            model_name="vtd",
            constraint=models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{11}$"),
                name="vtd_geoid_11_digits",
            ),
        ),
    ]
