"""Error-path coverage (SU-4b) for siege_utilities.geo.boundary_sources.

Forces the ValueError on an unknown Census boundary type and the
FileNotFoundError wrapper when the engine fails to load staged boundaries.
"""

import pytest

from siege_utilities.geo.boundary_sources import load_census_boundaries


class _FailingEngine:
    """Engine stand-in whose load_polygons raises a loadable error."""

    def load_polygons(self, path):
        raise OSError(f"no such object: {path}")


def test_load_census_boundaries_rejects_unknown_boundary_type():
    with pytest.raises(ValueError) as exc_info:
        load_census_boundaries(engine=None, boundary_type="not_a_boundary")
    assert "Unknown Census boundary type" in str(exc_info.value)


def test_load_census_boundaries_wraps_load_failure_as_file_not_found():
    with pytest.raises(FileNotFoundError) as exc_info:
        load_census_boundaries(engine=_FailingEngine(), boundary_type="county", year=2020)
    assert "not staged" in str(exc_info.value)
