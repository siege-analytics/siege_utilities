"""Root-import contracts for non-env-gated canonical helpers.

These are canonical (root-registered) symbols the per-symbol coverage scanner
(epic #1199) reported as direct=False because the existing suite exercises
them via submodule imports. Exercise them through the root `siege_utilities`
namespace with real assertions. All are pure-Python / no heavy deps.
"""

import logging

from siege_utilities import calculate_file_hash
from siege_utilities import remove_wrapping_quotes_and_trim
from siege_utilities import get_system_info
from siege_utilities import quick_smoke_test
from siege_utilities import log_warning
from siege_utilities import log_error
from siege_utilities import log_critical


def test_calculate_file_hash_is_sha256(tmp_path):
    target = tmp_path / "x.txt"
    target.write_text("hello\n", encoding="utf-8")
    digest = calculate_file_hash(str(target))
    # sha256 of the bytes "hello\n".
    assert digest == (
        "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"
    )


def test_remove_wrapping_quotes_and_trim():
    assert remove_wrapping_quotes_and_trim('  "hi"  ') == "hi"
    # No wrapping quotes: only surrounding whitespace is trimmed.
    assert remove_wrapping_quotes_and_trim("  plain  ") == "plain"


def test_get_system_info_reports_environment_keys():
    info = get_system_info()
    assert isinstance(info, dict)
    assert "platform" in info
    assert "python_executable" in info


def test_quick_smoke_test_passes_in_a_working_install():
    assert quick_smoke_test() is True


def test_log_helpers_emit_at_expected_levels(caplog):
    with caplog.at_level(logging.DEBUG):
        log_warning("contract-warn-msg")
        log_error("contract-error-msg")
        log_critical("contract-critical-msg")
    assert "contract-warn-msg" in caplog.text
    assert "contract-error-msg" in caplog.text
    assert "contract-critical-msg" in caplog.text
    levels = {r.levelno for r in caplog.records}
    assert logging.WARNING in levels
    assert logging.ERROR in levels
    assert logging.CRITICAL in levels
