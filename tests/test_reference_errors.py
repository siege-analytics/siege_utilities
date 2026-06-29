"""Error-path coverage (SU-4b) for siege_utilities.reference package init.

Forces the AttributeError raised by the lazy __getattr__ for unknown names.
"""

import pytest

import siege_utilities.reference as reference


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError) as exc_info:
        reference.no_such_reference_symbol_zzz
    assert "no_such_reference_symbol_zzz" in str(exc_info.value)


def test_getattr_dunder_call_raises_for_missing_name():
    with pytest.raises(AttributeError):
        reference.__getattr__("definitely_missing_symbol_qqq")
