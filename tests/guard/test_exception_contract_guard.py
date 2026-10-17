"""Executable checks for the stdlib-only exception contract guard."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_exception_contracts.py"
SPEC = importlib.util.spec_from_file_location("exception_guard", SCRIPT)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def run_guard(root):
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--root", str(root), "--list"],
        capture_output=True,
        text=True,
        timeout=30,
    )


def plant(root, source):
    package = root / "siege_utilities"
    package.mkdir(exist_ok=True)
    (package / "planted.py").write_text(source, encoding="utf-8")


@pytest.mark.parametrize(
    "annotation, body",
    [
        pytest.param(" -> object", "return pd.DataFrame()", id="empty-frame"),
        pytest.param(" -> object", "pass", id="pass"),
        pytest.param(" -> object", "continue", id="continue"),
        pytest.param(" -> object", "return 0", id="zero"),
        pytest.param(" -> object", "return self._create_default_user_profile()", id="default-factory"),
        pytest.param(" -> object", "return None, None, None", id="tuple"),
        pytest.param(" -> str", "return str(value)", id="str"),
        pytest.param(" -> dict", 'return {"label": "Unknown"}', id="unknown-dict"),
        pytest.param(" -> str", 'return f"unknown: {value}"', id="f-string"),
        pytest.param(" -> object", "return _create_placeholder_chart(value)", id="placeholder"),
        pytest.param(" -> object", "return _resolve_missing(value)", id="resolve-missing"),
        pytest.param(" -> object", "logger.warning('failed')", id="log-only"),
        pytest.param(" -> object", "gdf = pd.DataFrame()", id="empty-assignment"),
        pytest.param("", "return recovered_data", id="unannotated-data"),
    ],
)
def test_reviewer_fourteen_shapes_are_rejected(tmp_path, annotation, body):
    plant(
        tmp_path,
        f"def f(){annotation}:\n    for value in things:\n        try:\n            work()\n"
        f"        except ValueError:\n            {body}\n    return result\n",
    )
    result = run_guard(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.parametrize(
    "body",
    [
        'return {"label": "unknown"}',
        "return use_fallback(value)",
        "return self._default_profile()",
        "gdf: object = gpd.GeoDataFrame(columns=['geometry'])",
        "logger.error('failed'); return None, None, None",
    ],
)
def test_additional_default_spellings_are_rejected(tmp_path, body):
    plant(tmp_path, f"def f() -> object:\n    try:\n        work()\n    except ValueError:\n        {body}\n")
    assert run_guard(tmp_path).returncode == 1


def test_log_only_void_function_is_rejected(tmp_path):
    plant(tmp_path, "def export() -> None:\n    try:\n        work()\n    except OSError:\n        log.error('failed')\n")
    assert run_guard(tmp_path).returncode == 1


def test_nested_return_does_not_make_owner_a_data_function(tmp_path):
    plant(tmp_path, "def f():\n    def nested():\n        return 1\n    try:\n        work()\n    except ValueError:\n        pass\n")
    assert run_guard(tmp_path).returncode == 0


def test_converted_tree_has_zero_unlisted():
    result = run_guard(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "unlisted: 0; stale allow-list: 0" in result.stdout


@pytest.mark.parametrize(
    "catch",
    [
        "",
        " Exception",
        " BaseException",
        " (ValueError, Exception)",
        " builtins.Exception",
    ],
)
def test_broad_handlers_are_rejected(tmp_path, catch):
    plant(
        tmp_path,
        f"def f():\n    try:\n        work()\n    except{catch}:\n        log()\n",
    )
    result = run_guard(tmp_path)
    assert result.returncode == 1
    assert "BROAD" in result.stdout


@pytest.mark.parametrize(
    "body",
    [
        "pass",
        "continue",
        "return",
        "return None",
        "return 0",
        "return {}",
        "return []",
        'return "Unknown"',
        "return pd.DataFrame()",
        "return gpd.GeoDataFrame()",
        "return pd.DataFrame(columns=['name'])",
        "return pd.DataFrame([])",
        "return gpd.GeoDataFrame(data={}, geometry=[], crs=4326)",
    ],
)
def test_data_defaults_are_rejected(tmp_path, body):
    plant(
        tmp_path,
        f"def f() -> object:\n    for x in things:\n        try:\n            work()\n        except ValueError:\n            {body}\n",
    )
    assert run_guard(tmp_path).returncode == 1


@pytest.mark.parametrize("annotation", ["", " -> None", ' -> "None"'])
def test_non_data_functions_are_exempt_from_default_rule(tmp_path, annotation):
    plant(
        tmp_path,
        f"def f(){annotation}:\n    try:\n        work()\n    except ValueError:\n        pass\n",
    )
    assert run_guard(tmp_path).returncode == 0


def test_nested_function_raise_does_not_hide_swallow(tmp_path):
    plant(
        tmp_path,
        "def f():\n    try:\n        work()\n    except Exception:\n        def nested():\n            raise ValueError()\n",
    )
    assert run_guard(tmp_path).returncode == 1


@pytest.mark.parametrize("body", ["raise", "raise RuntimeError('failed') from exc"])
def test_reraises_are_accepted(tmp_path, body):
    plant(
        tmp_path,
        f"def f() -> object:\n    try:\n        work()\n    except Exception as exc:\n        {body}\n",
    )
    assert run_guard(tmp_path).returncode == 0


def test_finally_destructor_and_registered_signal_exemptions(tmp_path):
    plant(
        tmp_path,
        """import signal
class C:
    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

def cleanup() -> object:
    try:
        return work()
    finally:
        try:
            close()
        except Exception:
            pass

def shutdown(signum, frame):
    try:
        close()
    except Exception:
        pass
signal.signal(signal.SIGTERM, shutdown)
""",
    )
    assert run_guard(tmp_path).returncode == 0


def test_signal_name_alone_is_not_exempt(tmp_path):
    plant(
        tmp_path,
        "def signal_handler():\n    try:\n        work()\n    except Exception:\n        pass\n",
    )
    assert run_guard(tmp_path).returncode == 1


def test_allowlist_binds_handler_and_detects_stale_entries(tmp_path):
    source = "def f() -> object:\n    try:\n        work()\n    except Exception:\n        return None\n"
    plant(tmp_path, source)
    allow = {item["key"]: "Reviewed test fixture" for item in guard.scan(tmp_path)}
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/exception_contracts_allowlist.json").write_text(
        json.dumps(allow)
    )
    assert run_guard(tmp_path).returncode == 0
    plant(tmp_path, "\n\n" + source)
    assert run_guard(tmp_path).returncode == 0  # line shifts are stable
    plant(tmp_path, source.replace("return None", "return 0"))
    result = run_guard(tmp_path)
    assert result.returncode == 1 and "STALE" in result.stdout


def test_duplicate_handler_cannot_reuse_allowance(tmp_path):
    source = "def f() -> object:\n    try:\n        work()\n    except OSError:\n        return None\n"
    plant(tmp_path, source)
    allow = {item["key"]: "Reviewed test fixture" for item in guard.scan(tmp_path)}
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/exception_contracts_allowlist.json").write_text(
        json.dumps(allow)
    )
    plant(
        tmp_path,
        source + "    try:\n        work()\n    except OSError:\n        return None\n",
    )
    assert run_guard(tmp_path).returncode == 1


def test_empty_justification_rejected(tmp_path):
    plant(tmp_path, "")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/exception_contracts_allowlist.json").write_text('{"key": ""}')
    assert run_guard(tmp_path).returncode != 0


def test_fingerprint_ignores_empty_optional_ast_fields():
    """New Python AST fields must not invalidate unchanged reviewed handlers."""
    import ast

    node = ast.parse("def callback():\n    pass\n").body[0]
    before = guard.canonical_ast(node)
    # Python 3.12 added type_params; pre-3.12 nodes lack the field entirely.
    if "type_params" not in node._fields:
        node._fields = (*node._fields, "type_params")
    node.type_params = []
    assert guard.canonical_ast(node) == before
    # A populated field remains significant.
    node.type_params = [ast.Name(id="T", ctx=ast.Load())]
    assert guard.canonical_ast(node) != before
