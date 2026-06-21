"""Error-path coverage (SU-4b) for siege_utilities.connectors package init.

Forces the AttributeError raised by the lazy __getattr__ when an unknown
attribute is requested.
"""

import pytest

import siege_utilities.connectors as connectors


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError) as exc_info:
        connectors.this_attribute_does_not_exist_zzz
    assert "this_attribute_does_not_exist_zzz" in str(exc_info.value)


def test_getattr_dunder_call_raises_for_missing_name():
    # Exercise the module-level __getattr__ hook directly.
    with pytest.raises(AttributeError):
        connectors.__getattr__("definitely_missing_symbol_qqq")
