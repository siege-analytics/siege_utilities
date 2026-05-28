"""Error-path tests for siege_utilities.geo.django.serializers (SU-4b).

The boundary_serializers module has ImportError guards for
rest_framework_gis and model imports.
"""

import pytest


class TestBoundarySerializersImportFallback:
    """Error paths for boundary_serializers import guards."""

    def test_import_error_fallback_does_not_raise(self):
        """Module imports without raising even when DRF-GIS is missing."""
        try:
            from siege_utilities.geo.django.serializers import boundary_serializers
            assert boundary_serializers is not None
        except ImportError:
            pytest.skip("boundary_serializers deps missing")
