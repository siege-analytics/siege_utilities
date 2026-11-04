"""R-1809 battle-lane selection guard (#1809 / #1475).

The overnight battle wrapper must not run a broad ``pytest tests/``: its runner
has no Postgres service and must not execute the heavy notebook suite. Both of
its pytest invocations (the uv branch and the python branch) must therefore
carry the same exclusions as the main CI lane: ``-m "not integration and not
postgis"`` and ``--ignore=tests/test_notebooks.py``. This guard fails if either
exclusion is dropped from either branch.
"""
from pathlib import Path

WRAPPER = Path(__file__).resolve().parents[1] / "scripts" / "run_overnight_comprehensive.sh"
MARKER = '-m "not integration and not postgis"'
IGNORE = "--ignore=tests/test_notebooks.py"


def _pytest_invocations(text):
    """Join backslash-continued lines; return each full ``pytest tests/`` command."""
    joined = text.replace("\\\n", " ")
    return [line for line in joined.splitlines() if "pytest tests/" in line]


def test_wrapper_has_both_branch_invocations():
    invocations = _pytest_invocations(WRAPPER.read_text())
    assert len(invocations) == 2, invocations


def test_both_battle_invocations_exclude_postgis_and_notebooks():
    for cmd in _pytest_invocations(WRAPPER.read_text()):
        assert MARKER in cmd, f"battle invocation missing marker filter: {cmd}"
        assert IGNORE in cmd, f"battle invocation missing notebook ignore: {cmd}"
