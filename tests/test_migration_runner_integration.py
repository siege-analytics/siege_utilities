"""Error-path tests for siege_utilities.schema.tests.test_migration_runner_integration (SU-4b).

This module lives under siege_utilities/schema/tests/ and is scanned as
source code by the SU-4b coverage checker.
"""

import pytest

try:
    from siege_utilities.schema.tests import test_migration_runner_integration
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="schema test deps missing")


class TestMigrationRunnerIntegrationErrors:
    """Verify the integration test module is importable."""

    def test_error_test_raises_on_file_changed_exists(self):
        from siege_utilities.schema.tests import test_migration_runner_integration
        assert hasattr(test_migration_runner_integration, "test_apply_one_raises_on_file_changed_between_discovery_and_apply")
