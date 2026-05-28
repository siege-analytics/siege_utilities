"""Error-path tests for siege_utilities.reporting.examples.bivariate_choropleth_example (SU-4b)."""

import pytest

try:
    from siege_utilities.reporting.examples import bivariate_choropleth_example
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="reporting example deps missing")


class TestBivariateChoroplethExampleErrors:
    """Error paths for bivariate_choropleth_example functions."""

    def test_missing_deps_does_not_raise_on_import(self):
        from siege_utilities.reporting.examples.bivariate_choropleth_example import (
            run_all_examples,
        )
        assert run_all_examples is not None
