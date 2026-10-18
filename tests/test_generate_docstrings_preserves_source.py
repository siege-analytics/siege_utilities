"""Source preservation and safe invocation regressions for issue #1589."""

import ast
import difflib
import doctest
import importlib

import pytest

from scripts.check_no_stub_docstrings import _BAD_PHRASES
from siege_utilities.hygiene.generate_docstrings import (
    find_python_files,
    generate_docstring_template,
    process_python_file,
)


SOURCE = '''# SPDX-License-Identifier: MIT
import os  # noqa: F401

# Keep the spacing and explanatory comments.
VALUES = {"a": 1,   "b": 2}  # type: ignore

async def fetch(url: str):
    # Awaitable entry point.
    return url  # pragma: no cover

def plain(value):
    return value + 1  # Keep this comment too.
'''


@pytest.mark.parametrize("invariant", ["comments", "async", "stub_free", "formatting"])
def test_comment_survival(tmp_path, invariant):
    """The v4.0.0 writer loses comments, skips async, and emits rejected stubs."""
    target = tmp_path / "sample.py"
    target.write_text(SOURCE, encoding="utf-8")

    process_python_file(target, dry_run=False)

    output = target.read_text(encoding="utf-8")
    if invariant == "comments":
        for line in SOURCE.splitlines():
            if "#" in line:
                assert line in output.splitlines()
    elif invariant == "async":
        functions = [node for node in ast.walk(ast.parse(output)) if isinstance(node, ast.AsyncFunctionDef)]
        assert len(functions) == 1
        assert ast.get_docstring(functions[0])
    elif invariant == "stub_free":
        assert all(marker not in output for marker in _BAD_PHRASES)
    else:
        diff = difflib.SequenceMatcher(a=SOURCE.splitlines(True), b=output.splitlines(True))
        assert all(op in ("equal", "insert") for op, *_ in diff.get_opcodes())
    plain = next(node for node in ast.walk(ast.parse(output)) if isinstance(node, ast.FunctionDef))
    assert ast.get_docstring(plain)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "latin-1"])
def test_preserves_encoding_newlines_and_missing_final_newline(tmp_path, newline, encoding):
    source = f'# coding: {encoding}\n# café\ndef greet(name):\n\treturn f"héllo {{name}}"'
    original = source.replace("\n", newline).encode(encoding)
    target = tmp_path / "encoded.py"
    target.write_bytes(original)
    process_python_file(target, dry_run=False)
    output = target.read_bytes()
    assert not output.endswith((b"\n", b"\r"))
    assert all(line.endswith(newline.encode()) for line in output.splitlines(True)[:-1])
    diff = difflib.SequenceMatcher(a=original.splitlines(True), b=output.splitlines(True))
    assert all(op in ("equal", "insert") for op, *_ in diff.get_opcodes())
    assert ast.get_docstring(ast.parse(output).body[0])
    process_python_file(target, dry_run=False)
    assert target.read_bytes() == output


def test_nested_decorated_and_multiline_definitions(tmp_path):
    source = '''def outer(
    value: str = '"""',
):  # signature comment
    # The decorator must stay attached to inner.
    @(
        decorate
    )
    async def inner(item):
        return item
    class Holder:
        @staticmethod
        def method(item):
            return item
    return inner

def numeric_constant():
    42
    return 1

def documented():
    """Keep this exact docstring."""
    return 2
'''
    target = tmp_path / "nested.py"
    target.write_text(source)
    process_python_file(target, dry_run=False)
    output = target.read_text()
    tree = ast.parse(output)
    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert len(functions) == 5
    assert all(ast.get_docstring(node) for node in functions)
    assert ast.get_docstring(tree.body[-1]) == "Keep this exact docstring."
    diff = difflib.SequenceMatcher(a=source.splitlines(True), b=output.splitlines(True))
    assert all(op in ("equal", "insert") for op, *_ in diff.get_opcodes())


@pytest.mark.parametrize("source", ["def inline(): return 1\n", "async def inline(\n): return 1\n"])
def test_inline_suite_is_left_unchanged_with_warning(tmp_path, monkeypatch, source):
    module = importlib.import_module("siege_utilities.hygiene.generate_docstrings")
    warnings = []
    monkeypatch.setattr(module, "log_warning", warnings.append)
    target = tmp_path / "inline.py"
    target.write_text(source)
    process_python_file(target, dry_run=False)
    assert target.read_text() == source
    assert any("inline suite requires reformatting" in warning for warning in warnings)


@pytest.mark.parametrize("entry", ["file", "main", "cli", "cli_dry_run", "cli_write", "cli_apply"])
def test_writing_requires_explicit_opt_in(tmp_path, monkeypatch, entry):
    module = importlib.import_module("siege_utilities.hygiene.generate_docstrings")
    target = tmp_path / "sample.py"
    target.write_text(SOURCE)
    if entry == "file":
        module.process_python_file(target)
    elif entry == "main":
        assert module.main(base_path=tmp_path)
    else:
        flags = {"cli": [], "cli_dry_run": ["--dry-run"], "cli_write": ["--write"], "cli_apply": ["--apply"]}
        monkeypatch.setattr("sys.argv", ["generate_docstrings", "--path", str(tmp_path), *flags[entry]])
        assert module.cli()
    if entry in ("cli_write", "cli_apply"):
        assert target.read_text() != SOURCE
        assert ast.get_docstring(ast.parse(target.read_text()).body[-1])
    else:
        assert target.read_text() == SOURCE


def test_file_filter_uses_components_and_excludes_migrations(tmp_path):
    root = tmp_path / "builds" / "repo"
    keep = ["distributed/spark.py", "geo/redistricting.py", "data/redistricting_data_hub.py",
            "dist_helper.py", "build_helpers/tool.py", "migrations_helper.py"]
    exclude = ["__init__.py", "build/module.py", "dist/module.py", ".git/module.py",
               "__pycache__/module.py", ".pytest_cache/module.py", "geo/migrations/0001_initial.py",
               "migrations/nested/helper.py"]
    for relative in keep + exclude:
        path = root / "siege_utilities" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    expected = sorted(root / "siege_utilities" / relative for relative in keep)
    assert find_python_files(root) == expected
    assert find_python_files(root / "siege_utilities") == expected


def test_signature_details_and_examples_are_safe(tmp_path):
    source = '''def method(self, item: int, /, name: str = "café", *args, enabled: bool = True, **kwargs) -> str:
    return name
'''
    target = tmp_path / "method.py"
    target.write_text(source)
    process_python_file(target, dry_run=False)
    docstring = ast.get_docstring(ast.parse(target.read_text()).body[0])
    for param in ("item (int)", "name (str)", "args (Any)", "enabled (bool)", "kwargs (Any)"):
        assert param in docstring
    assert "self (" not in docstring
    assert "defaults to 'café'" in docstring
    assert "str: Return value." in docstring
    for text in (docstring, generate_docstring_template("not_exported")):
        assert all(marker not in text for marker in _BAD_PHRASES)
        examples = doctest.DocTestParser().get_examples(text)
        assert examples
        assert all(example.options.get(doctest.SKIP) for example in examples)
