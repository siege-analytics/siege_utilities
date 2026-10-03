"""End-to-end code-analysis and reporting pipeline over real inputs.

Exercises, against real files and the real loaded package graph, the
introspection/reporting fixes from this sweep:
- process_python_file edits a real file on disk without crashing and adds a
  missing function docstring (#1304)
- analyze_module recurses the loaded package graph and terminates instead of
  overflowing the stack (#1309)
- get_test_report reports a real timestamp and boolean health fields rather
  than the working directory and dict-as-truthiness (#1308)

All pure-Python: no Spark, no network, no GDAL. (run_comprehensive_test is
intentionally not exercised here: it executes the entire pytest suite, which
would recurse into this file.)
"""

import ast
import datetime as dt

import pytest

from siege_utilities import process_python_file
from siege_utilities import analyze_module
from siege_utilities import get_test_report


@pytest.mark.e2e
class TestCodeAnalysisPipelineE2E:
    def _func_docstring(self, source, name):
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return ast.get_docstring(node)
        raise AssertionError(f"function {name!r} not found")

    def test_process_python_file_adds_missing_function_docstring(
        self, tmp_path
    ):
        src = tmp_path / "sample_module.py"
        src.write_text(
            "import os\n"
            "\n"
            "def add(a, b):\n"
            "    return a + b\n"
        )
        # before: the function has no docstring
        assert self._func_docstring(src.read_text(), "add") is None

        result = process_python_file(str(src))

        # the helper edits in place and returns None; the real-path crash the
        # fix addressed would raise here instead.
        assert result is None
        assert self._func_docstring(src.read_text(), "add") is not None

    def test_analyze_module_recurses_without_stack_overflow(self):
        import siege_utilities as pkg

        # The loaded package graph is the input that previously overflowed the
        # stack; completing at all is the regression guard for #1309.
        report = analyze_module(pkg, "siege_utilities")

        assert isinstance(report, dict)
        assert report["function_count"] > 0
        assert report["class_count"] > 0

        submodules = report["submodules"]
        assert isinstance(submodules, dict) and submodules
        # at least one child is itself a fully-formed analysis dict, proving
        # the recursion descended and still terminated.
        child = next(iter(submodules.values()))
        assert isinstance(child, dict)
        assert "function_count" in child

    def test_get_test_report_has_real_timestamp_and_bool_health(self):
        report = get_test_report()

        assert isinstance(report, dict)
        # timestamp is an ISO datetime, not the working directory (#1308).
        parsed = dt.datetime.fromisoformat(report["timestamp"])
        assert isinstance(parsed, dt.datetime)

        assert isinstance(report["environment_healthy"], bool)
        assert isinstance(report["smoke_test_passed"], bool)
        deps = report["dependencies"]
        assert isinstance(deps, dict) and deps
        assert all(isinstance(v, bool) for v in deps.values())
