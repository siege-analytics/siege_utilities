"""
Areal interpolation for transferring data between geographic boundaries.

Wraps PySAL's Tobler library to provide a consistent interface for
extensive (population) and intensive (median income) variable interpolation.

Example::

    from siege_utilities.geo.interpolation import interpolate_extensive, interpolate_intensive

    # Transfer population counts from 2010 tracts to 2020 tracts
    result = interpolate_extensive(
        source_gdf=tracts_2010,
        target_gdf=tracts_2020,
        variables=["total_pop", "housing_units"],
    )

    # Transfer median income (rate) from 2010 to 2020 tracts
    result = interpolate_intensive(
        source_gdf=tracts_2010,
        target_gdf=tracts_2020,
        variables=["median_income", "poverty_rate"],
    )
"""

from .areal import (
    ArealInterpolationResult,
    interpolate_areal,
    interpolate_extensive,
    interpolate_intensive,
    compute_area_weights,
)

__all__ = [
    "ArealInterpolationResult",
    "interpolate_areal",
    "interpolate_extensive",
    "interpolate_intensive",
    "compute_area_weights",
]
