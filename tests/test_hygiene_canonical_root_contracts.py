"""Root-import contracts for canonical hygiene/generate_docstrings symbols.

These functions are canonical (root-registered via _register_lazy) but the
existing suite imports them from the submodule, so the per-symbol coverage
scanner (epic #1199) does not credit them. Exercise them through the root
`siege_utilities` namespace with real assertions.
"""

from pathlib import Path

import pytest

from siege_utilities import analyze_function_signature
from siege_utilities import generate_docstring_template
from siege_utilities import process_python_file


def test_analyze_function_signature_reports_params_and_return():
    def sample(count: int, name: str = "hi") -> bool:
        return bool(count) and bool(name)

    params, return_desc = analyze_function_signature(sample)
    assert any("count (int)" in p for p in params)
    assert any("name (str)" in p and "defaults to 'hi'" in p for p in params)
    assert "bool" in return_desc


def test_generate_docstring_template_includes_name_and_example():
    out = generate_docstring_template("fetch_from_url")
    assert "Fetch From Url" in out
    assert "Example:" in out
    assert "siege_utilities.fetch_from_url(" in out


def test_process_python_file_adds_missing_docstring(tmp_path, monkeypatch):
    pytest.importorskip(
        "astor", reason="astor is required to rewrite source with docstrings"
    )
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "needs.py"
    target.write_text("def undocumented(value):\n    return value + 1\n")
    process_python_file(Path("needs.py"))
    rewritten = target.read_text()
    assert '"""' in rewritten
    assert "Undocumented." in rewritten
