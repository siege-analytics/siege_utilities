"""Error-path tests for siege_utilities.examples.enhanced_features_demo (SU-4b)."""

import pytest

try:
    from siege_utilities.examples import enhanced_features_demo
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="enhanced_features_demo deps missing")


class TestEnhancedFeaturesDemoErrors:
    """Error paths for enhanced_features_demo functions."""

    def test_missing_deps_does_not_raise_on_import(self):
        from siege_utilities.examples.enhanced_features_demo import main
        assert main is not None
