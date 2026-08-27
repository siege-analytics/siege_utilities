"""Tests for #1048: settings._coerce must raise on malformed env var.

Earlier behavior silently warned and returned the library default,
which hid deployment-config bugs (a typo'd SIEGE_STORAGE_CRS=badstr
would resolve to the default without the operator noticing). Per SU-1,
malformed input at a config boundary raises.
"""

from __future__ import annotations

import pytest

from siege_utilities.conf import Settings


@pytest.fixture(autouse=True)
def reset_settings() -> None:
    """Ensure a fresh Settings singleton per test."""
    Settings._reset()
    yield
    Settings._reset()


def test_coerce_malformed_int_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed SIEGE_<INT_SETTING> raises ValueError with actionable message."""
    # STORAGE_CRS is int-typed in DEFAULTS
    monkeypatch.setenv("SIEGE_STORAGE_CRS", "not-a-number")

    s = Settings()
    with pytest.raises(ValueError) as exc_info:
        _ = s.STORAGE_CRS

    msg = str(exc_info.value)
    assert "SIEGE_STORAGE_CRS" in msg
    assert "not-a-number" in msg
    assert "integer" in msg


def test_coerce_malformed_float_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed SIEGE_<FLOAT_SETTING> raises ValueError with actionable message.

    Uses monkeypatch to inject a float-typed default so the test does not
    couple to which specific settings happen to be float today.
    """
    import siege_utilities.conf as conf_mod

    monkeypatch.setattr(
        conf_mod, "DEFAULTS", {**conf_mod.DEFAULTS, "TEST_FLOAT": 1.5}
    )
    monkeypatch.setenv("SIEGE_TEST_FLOAT", "not-a-float")

    s = Settings()
    with pytest.raises(ValueError) as exc_info:
        _ = s.TEST_FLOAT

    msg = str(exc_info.value)
    assert "SIEGE_TEST_FLOAT" in msg
    assert "not-a-float" in msg
    assert "number" in msg


def test_coerce_valid_int_returns_parsed_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid int env var round-trips through _coerce cleanly."""
    monkeypatch.setenv("SIEGE_STORAGE_CRS", "4326")

    s = Settings()
    assert s.STORAGE_CRS == 4326


def test_coerce_bool_env_var_still_parses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bool coercion path unchanged — no raise for unrecognised bool strings."""
    # Bool coercion is `val.lower() in ("true", "1", "yes")` — anything else
    # is False. This is not the SU-1 case; there's no notion of "malformed"
    # for bools without breaking many valid deployments.
    import siege_utilities.conf as conf_mod

    monkeypatch.setattr(
        conf_mod, "DEFAULTS", {**conf_mod.DEFAULTS, "TEST_BOOL": True}
    )

    for val, expected in [("true", True), ("1", True), ("yes", True),
                          ("false", False), ("no", False), ("", False)]:
        monkeypatch.setenv("SIEGE_TEST_BOOL", val)
        Settings._reset()
        s = Settings()
        assert s.TEST_BOOL is expected, f"SIEGE_TEST_BOOL={val!r}"
