"""Error-path coverage (SU-4b) for siege_utilities.geo.capabilities.

Exercises the ``except ImportError`` guard in _probe by probing a module
that cannot be imported.
"""

from siege_utilities.geo.capabilities import _probe


def test_probe_returns_false_for_missing_module():
    # The except ImportError branch must fire and yield False.
    assert _probe("siege_utilities_no_such_module_zzz") is False


def test_probe_returns_true_for_importable_module():
    # Sanity anchor: a real module probes True (guard test isn't vacuous).
    assert _probe("json") is True
