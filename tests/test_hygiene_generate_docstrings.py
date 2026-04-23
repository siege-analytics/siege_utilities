"""First tests for siege_utilities.hygiene.generate_docstrings (ELE-2419)."""
from __future__ import annotations

import ast
import textwrap

import pytest

from siege_utilities.hygiene.generate_docstrings import (
    DocstringAdder,
    analyze_function_signature,
    categorize_function,
    find_python_files,
    generate_docstring_template,
    process_python_file,
)


class TestCategorizeFunction:
    @pytest.mark.parametrize(
        "name,expected_category",
        [
            ("log_info", "Logging"),
            ("debug_stuff", "Logging"),
            ("read_file", "File Operations"),
            ("download_data", "Remote Operations"),
            ("geo_helper", "Geospatial"),
            ("spark_setup", "Distributed Computing"),
            ("hash_value", "Hashing"),
            ("clean_string", "String Utilities"),
            ("config_loader", "Configuration"),
            ("mystery_func", "Utilities"),
        ],
    )
    def test_category_dispatch(self, name, expected_category):
        category, _desc = categorize_function(name)
        assert category == expected_category


class TestAnalyzeFunctionSignature:
    def test_no_annotations_defaults_to_any(self):
        def f(a, b):
            return a + b

        params, ret = analyze_function_signature(f)
        assert len(params) == 2
        assert "a (Any)" in params[0]
        assert "b (Any)" in params[1]
        assert "Any" in ret

    def test_annotations_extracted(self):
        def f(count: int, name: str = "hi") -> bool:
            return False

        params, ret = analyze_function_signature(f)
        assert "count (int)" in params[0]
        assert "name (str)" in params[1]
        assert "defaults to 'hi'" in params[1]
        assert "bool" in ret

    def test_builtin_without_signature_returns_empty(self):
        """`len` has no inspectable signature on all Python versions; function
        should return the Any fallback without raising."""
        # Use a lambda that forces inspect to fail in certain contexts
        params, ret = analyze_function_signature(lambda: None)
        assert params == []
        assert "Any" in ret


class TestGenerateDocstringTemplate:
    def test_includes_readable_name_and_category(self):
        out = generate_docstring_template("fetch_from_url")
        assert "Fetch From Url" in out
        assert "Remote Operations" in out or "Handle remote files" in out

    def test_with_function_object_includes_param(self):
        def my_func(x: int) -> str:
            return str(x)

        out = generate_docstring_template("my_func", my_func)
        assert "Args:" in out
        assert "x (int)" in out
        assert "Returns:" in out
        assert "str" in out

    def test_includes_example_block(self):
        out = generate_docstring_template("some_thing")
        assert "Example:" in out
        assert ">>> import siege_utilities" in out
        assert "siege_utilities.some_thing(" in out


class TestDocstringAdder:
    def test_adds_docstring_to_undocumented_function(self):
        src = textwrap.dedent(
            """
            def greet(name):
                return f'hi {name}'
            """
        )
        tree = ast.parse(src)
        adder = DocstringAdder(module_name="t")
        adder.visit(tree)
        assert adder.functions_processed == 1
        assert adder.functions_skipped == 0
        fn = tree.body[0]
        first = fn.body[0]
        assert isinstance(first, ast.Expr)
        assert isinstance(first.value, ast.Constant)
        assert "Greet" in first.value.value

    def test_skips_already_documented_function(self):
        src = textwrap.dedent(
            '''
            def greet(name):
                """Already documented."""
                return name
            '''
        )
        tree = ast.parse(src)
        adder = DocstringAdder()
        adder.visit(tree)
        assert adder.functions_processed == 0
        assert adder.functions_skipped == 1

    def test_skips_private_functions(self):
        src = textwrap.dedent(
            """
            def _internal(x):
                return x
            """
        )
        tree = ast.parse(src)
        adder = DocstringAdder()
        adder.visit(tree)
        assert adder.functions_processed == 0
        assert adder.functions_skipped == 0


class TestFindPythonFiles:
    def test_returns_sorted_list_excluding_init_and_cache(self, tmp_path):
        pkg = tmp_path / "siege_utilities"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "a.py").write_text("x = 1")
        (pkg / "b.py").write_text("y = 2")
        (pkg / "__pycache__").mkdir()
        (pkg / "__pycache__" / "garbage.py").write_text("")
        subdir = pkg / "sub"
        subdir.mkdir()
        (subdir / "c.py").write_text("z = 3")

        result = find_python_files(tmp_path)
        names = [p.name for p in result]
        assert names == sorted(names)
        assert "a.py" in names
        assert "b.py" in names
        assert "c.py" in names
        assert "__init__.py" not in names
        assert "garbage.py" not in names


class TestProcessPythonFile:
    def test_syntax_error_returns_false(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        bad = tmp_path / "bad.py"
        bad.write_text("def :\n    pass\n")
        assert process_python_file(bad) is False

    def test_no_changes_needed_returns_true(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "ok.py"
        f.write_text('def greet():\n    """already."""\n    return 1\n')
        assert process_python_file(f) is True
        # Should not have been rewritten
        assert "already" in f.read_text()
