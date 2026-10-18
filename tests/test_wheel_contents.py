"""Wheel contents: only siege_utilities ships, with its runtime data (#1420).

The CI ``build`` job builds the real wheel and runs
``scripts/check_wheel_contents.py`` on it. These tests pin the packaging
configuration that check depends on and exercise the checker against
synthetic wheels shaped like the defective published ones.
"""

from __future__ import annotations

import fnmatch
import importlib.util
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_wheel_contents.py"
SPEC = importlib.util.spec_from_file_location("check_wheel_contents", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
SETUPTOOLS = PYPROJECT["tool"]["setuptools"]


def _required() -> set[str]:
    required, errors = checker.required_data_files(ROOT)
    assert errors == []
    return required


def _wheel(tmp_path: Path, names: list[str]) -> Path:
    path = tmp_path / "siege_utilities-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as zf:
        for name in names:
            zf.writestr(name, "")
    return path


def _good_names() -> list[str]:
    return [
        "siege_utilities/__init__.py",
        "siege_utilities-0.0.0.dist-info/METADATA",
        "siege_utilities-0.0.0.dist-info/RECORD",
        *sorted(_required()),
    ]


def test_packages_find_is_an_allow_list_of_the_library():
    find = SETUPTOOLS["packages"]["find"]
    assert find["include"] == ["siege_utilities*"]


def test_package_data_declares_every_file_the_code_loads():
    patterns = SETUPTOOLS["package-data"]["siege_utilities"]
    prefix = "siege_utilities/"
    uncovered = sorted(
        path
        for path in _required()
        if not any(fnmatch.fnmatch(path[len(prefix):], pat) for pat in patterns)
    )
    assert uncovered == []


def test_required_data_includes_migrations_and_configs():
    required = _required()
    assert any(p.startswith("siege_utilities/political/migrations/V0001") for p in required)
    assert "siege_utilities/configs/default/user_profile.yaml" in required
    assert "siege_utilities/py.typed" in required


def test_every_file_relative_reference_in_the_package_is_declared():
    assert checker.find_reference_modules(ROOT) == set(checker.FILE_RELATIVE_REFERENCES)


def test_clean_wheel_passes(tmp_path):
    assert checker.check_wheel(_wheel(tmp_path, _good_names()), _required()) == []


def test_stray_top_level_package_fails(tmp_path):
    names = _good_names() + ["spikes/parsons_adapter/roundtrip_matrix.py"]
    problems = checker.check_wheel(_wheel(tmp_path, names), _required())
    assert any("spikes" in p and "top-level" in p for p in problems)


def test_missing_sql_migration_fails(tmp_path):
    names = [n for n in _good_names() if not n.endswith(".sql")]
    problems = checker.check_wheel(_wheel(tmp_path, names), _required())
    assert any("V0001__create_political_schema.sql" in p for p in problems)


@pytest.mark.parametrize(
    "stray",
    [
        "siege_utilities/examples/enhanced_features_demo 2.py",
        "siege_utilities/geo/django/migrations/0010_seat_state_constraint 2.py",
        "siege_utilities/a\tb.py",
    ],
)
def test_whitespace_in_member_name_fails(tmp_path, stray):
    problems = checker.check_wheel(_wheel(tmp_path, _good_names() + [stray]), _required())
    assert any("whitespace" in p and repr(stray) in p for p in problems)


def test_bytecode_fails(tmp_path):
    names = _good_names() + ["siege_utilities/__pycache__/__init__.cpython-311.pyc"]
    problems = checker.check_wheel(_wheel(tmp_path, names), _required())
    assert any("bytecode" in p for p in problems)


def test_unlisted_reference_is_a_config_error(tmp_path):
    pkg = tmp_path / "siege_utilities"
    pkg.mkdir()
    (pkg / "py.typed").write_text("")
    (pkg / "loader.py").write_text(
        "from pathlib import Path\nDATA = Path(__file__).parent / 'data.csv'\n"
    )
    _, errors = checker.required_data_files(tmp_path)
    assert any("siege_utilities/loader.py" in e and "not listed" in e for e in errors)


def test_main_exit_codes(tmp_path):
    good = _wheel(tmp_path, _good_names())
    assert checker.main([str(good)]) == 0
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    bad = _wheel(bad_dir, _good_names() + ["spikes/__init__.py"])
    assert checker.main([str(bad)]) == 1
