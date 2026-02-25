"""
Library-wide default values for siege_utilities settings.

Categories are documented with comments. New defaults should be added
to the appropriate section. The dict is flat — no nesting.

Trial run: CRS/geo + Census defaults. Future PRs add remaining categories.
"""

DEFAULTS: dict = {
    # ── Coordinate Reference Systems ──
    "STORAGE_CRS": 4269,          # NAD83 — what Census TIGER ships as
    "PROJECTION_CRS": 2163,       # US National Atlas Equal Area (meters)
    "INPUT_CRS": 4269,            # Assumed CRS for incoming data without metadata
    "WEB_CRS": 4326,              # WGS84 — for web map output (Leaflet, Mapbox)
    "DISTANCE_UNITS": "miles",    # Default distance units for user-facing output

    # ── Census / TIGER ──
    "CENSUS_TIMEOUT": 45,         # Seconds per Census API/download request
    "CENSUS_RETRY_ATTEMPTS": 5,
    "CENSUS_CACHE_TIMEOUT": 86400,  # 24 hours
    "CENSUS_DEFAULT_YEAR": 2023,
    "CENSUS_DEFAULT_VINTAGE": "2020",  # Decennial vintage for boundary alignment

    # ── Spatial Engine ──
    "SPATIAL_BACKEND": "geopandas",
    "TABULAR_ENGINE": "pandas",     # pandas | polars | spark
}
