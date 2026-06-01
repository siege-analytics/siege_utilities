"""Shared admin-level area constants for H3 and S2 resolution selection.

The average areas below are rough midpoints across the entire US. The
variance within a level (e.g. NY tract vs WY tract) is huge. The resolution
returned by callers is a starting point; tune up or down by +/-1 if the
polygons you actually have are systematically larger or smaller.
"""

__all__ = [
    'ADMIN_LEVEL_AVG_AREA_KM2',
    'ADMIN_LEVEL_ALIASES',
]

ADMIN_LEVEL_AVG_AREA_KM2 = {
    "state": 196_600.0,
    "county": 3_000.0,
    "zcta": 110.0,
    "tract": 5.0,
    "block_group": 1.0,
    "block": 0.04,
}

ADMIN_LEVEL_ALIASES = {
    "states": "state",
    "us_state": "state",
    "counties": "county",
    "us_county": "county",
    "zip": "zcta",
    "zip_code": "zcta",
    "zipcode": "zcta",
    "zctas": "zcta",
    "tracts": "tract",
    "census_tract": "tract",
    "bg": "block_group",
    "block_groups": "block_group",
    "blockgroup": "block_group",
    "blocks": "block",
    "census_block": "block",
}
