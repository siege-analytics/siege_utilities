"""
Services for populating Census boundary and NCES education data.

Imports are deferred to avoid requiring Django setup at import time.
Use: ``from siege_utilities.geo.django.services.nces_service import NCESPopulationService``
"""


def __getattr__(name):
    """Lazy imports — avoids Django setup requirement at package import time."""
    _map = {
        "BoundaryPopulationService": ".population_service",
        "DemographicPopulationService": ".demographic_service",
        "CrosswalkPopulationService": ".crosswalk_service",
        "TimeseriesService": ".timeseries_service",
        "DemographicRollupService": ".rollup_service",
        "UrbanicityClassificationService": ".urbanicity_service",
        "NCESPopulationService": ".nces_service",
        "NLRBPopulationService": ".nlrb_service",
        "TimezonePopulationService": ".timezone_service",
    }
    if name in _map:
        import importlib

        mod = importlib.import_module(_map[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BoundaryPopulationService",
    "DemographicPopulationService",
    "CrosswalkPopulationService",
    "TimeseriesService",
    "DemographicRollupService",
    "UrbanicityClassificationService",
    "NCESPopulationService",
    "NLRBPopulationService",
    "TimezonePopulationService",
]
