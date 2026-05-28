"""Error-path tests for siege_utilities.geo.boundary_sources (SU-4b)."""

import pytest

from siege_utilities.geo.boundary_sources import load_census_boundaries


class TestLoadCensusBoundariesErrors:
    """Error paths for load_census_boundaries."""

    def test_invalid_boundary_type_raises(self):
        """Unknown boundary type must raise ValueError."""
        with pytest.raises(ValueError, match="Unknown Census boundary type"):
            load_census_boundaries(None, "galaxy_cluster")

    def test_empty_boundary_type_raises(self):
        """Empty boundary type must raise ValueError."""
        with pytest.raises(ValueError, match="Unknown Census boundary type"):
            load_census_boundaries(None, "")

    def test_valid_type_with_bad_engine_raises(self):
        """Valid boundary type with non-engine raises (engine.load_polygons fails)."""
        with pytest.raises((AttributeError, FileNotFoundError)):
            load_census_boundaries(object(), "tract")
