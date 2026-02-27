"""
Unit tests for BoundaryManager and BoundaryQuerySet.

Tests the spatial query helpers including nearest(), within_distance(),
containing_point(), etc. These tests verify the method signatures and
QuerySet construction without requiring a full PostGIS database.
"""

import inspect

import pytest


class TestBoundaryQuerySetNearest:
    """Tests for BoundaryQuerySet.nearest() method."""

    def test_nearest_imported_from_module(self):
        """Verify nearest is defined on BoundaryQuerySet."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryQuerySet

        assert hasattr(BoundaryQuerySet, "nearest")

    def test_nearest_accepts_srid_parameter(self):
        """Verify nearest() accepts srid parameter."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryQuerySet

        sig = inspect.signature(BoundaryQuerySet.nearest)
        params = list(sig.parameters.keys())
        assert "srid" in params
        assert sig.parameters["srid"].default == 4326

    def test_nearest_max_distance_default_none(self):
        """Verify max_distance_m defaults to None."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryQuerySet

        sig = inspect.signature(BoundaryQuerySet.nearest)
        assert sig.parameters["max_distance_m"].default is None


class TestBoundaryManagerNearest:
    """Tests for BoundaryManager.nearest() proxy."""

    def test_nearest_on_manager(self):
        """Verify nearest is accessible on BoundaryManager."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryManager

        assert hasattr(BoundaryManager, "nearest")

    def test_manager_nearest_accepts_srid(self):
        """Verify BoundaryManager.nearest() passes srid through."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryManager

        sig = inspect.signature(BoundaryManager.nearest)
        assert "srid" in sig.parameters


class TestContainingPointSRID:
    """Tests for containing_point() SRID parameterization."""

    def test_containing_point_accepts_srid(self):
        """Verify containing_point() accepts srid parameter."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryQuerySet

        sig = inspect.signature(BoundaryQuerySet.containing_point)
        assert "srid" in sig.parameters
        assert sig.parameters["srid"].default == 4326

    def test_manager_containing_point_accepts_srid(self):
        """Verify BoundaryManager.containing_point() passes srid through."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryManager

        sig = inspect.signature(BoundaryManager.containing_point)
        assert "srid" in sig.parameters


class TestDistanceMeasure:
    """Tests for proper geodesic distance usage (D(m=...) instead of degree hack)."""

    def test_within_distance_uses_measure_d(self):
        """Verify within_distance uses django.contrib.gis.measure.D."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryQuerySet

        source = inspect.getsource(BoundaryQuerySet.within_distance)
        # Should use D(m=...) not the old degree approximation
        assert "D(m=" in source
        assert "/ 1000 / 111" not in source

    def test_nearest_uses_measure_d_for_max_distance(self):
        """Verify nearest uses D(m=...) for max_distance filter."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryQuerySet

        source = inspect.getsource(BoundaryQuerySet.nearest)
        assert "D(m=" in source
        assert "/ 1000 / 111" not in source

    def test_d_imported(self):
        """Verify D is imported from django.contrib.gis.measure."""
        from siege_utilities.geo.django.managers import boundary_manager

        assert hasattr(boundary_manager, "D")


class TestBulkCreateSRID:
    """Tests for bulk_create_from_geodataframe() SRID parameterization."""

    def test_bulk_create_accepts_srid(self):
        """Verify bulk_create_from_geodataframe accepts srid parameter."""
        from siege_utilities.geo.django.managers.boundary_manager import BoundaryManager

        sig = inspect.signature(BoundaryManager.bulk_create_from_geodataframe)
        assert "srid" in sig.parameters
        assert sig.parameters["srid"].default == 4326
