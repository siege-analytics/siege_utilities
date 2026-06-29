"""Error-path coverage (SU-4b) for siege_utilities.political.readers.

Forces the ValueError raised by _quote_ident on unsafe SQL identifiers.
"""

import pytest

from siege_utilities.political.readers import _qualified, _quote_ident


def test_quote_ident_rejects_empty_identifier():
    with pytest.raises(ValueError) as exc_info:
        _quote_ident("")
    assert "unsafe identifier" in str(exc_info.value)


@pytest.mark.parametrize(
    "bad",
    ["bad name", "table;DROP", "a-b", "quote'd", "semi;colon", "star*"],
)
def test_quote_ident_rejects_unsafe_characters(bad):
    with pytest.raises(ValueError):
        _quote_ident(bad)


def test_qualified_propagates_value_error_for_unsafe_table():
    # _qualified delegates to _quote_ident, so the unsafe-identifier guard
    # must surface here too rather than producing an injectable string.
    with pytest.raises(ValueError):
        _qualified("evil; DROP TABLE x")


def test_quote_ident_accepts_safe_identifier():
    # Sanity anchor: the guard does not reject legitimate identifiers.
    assert _quote_ident("valid_name_1") == '"valid_name_1"'
