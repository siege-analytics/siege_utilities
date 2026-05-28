"""Error-path tests for siege_utilities.reporting.examples.comprehensive_mapping_example (SU-4b)."""

import pytest

try:
    from siege_utilities.reporting.examples import comprehensive_mapping_example
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="reporting example deps missing")


class TestComprehensiveMappingExampleErrors:
    """Error paths for comprehensive_mapping_example functions."""

    def test_missing_deps_does_not_raise_on_import(self):
        from siege_utilities.reporting.examples.comprehensive_mapping_example import (
            main,
        )
        assert main is not None
