# ================================================================
# FILE: test_architecture.py
# ================================================================
"""
Tests for siege_utilities.development.architecture module.

Covers:
- analyze_function / analyze_class / analyze_module (introspection helpers)
- generate_text_diagram / generate_markdown_diagram / generate_rst_diagram
- generate_architecture_diagram (orchestrator, all formats + file output)
- generate_requirements_txt / generate_pyproject_toml / generate_poetry_toml / generate_uv_toml
- analyze_package_structure (with a synthetic package)
"""

import json
import textwrap
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from siege_utilities.development.architecture import (
    analyze_class,
    analyze_function,
    analyze_module,
    analyze_package_structure,
    generate_architecture_diagram,
    generate_markdown_diagram,
    generate_poetry_toml,
    generate_pyproject_toml,
    generate_requirements_txt,
    generate_rst_diagram,
    generate_text_diagram,
    generate_uv_toml,
)


# ----------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------

def _sample_function(x: int, y: str = "hello") -> bool:
    """A sample function for testing introspection."""
    return True


class _SampleClass:
    """A sample class for testing introspection."""

    def public_method(self, a: int) -> None:
        """Do something public."""
        pass

    def another_method(self) -> str:
        """Return a string."""
        return ""

    def _private_method(self):
        pass


@pytest.fixture
def sample_function():
    return _sample_function


@pytest.fixture
def sample_class():
    return _SampleClass


@pytest.fixture
def minimal_structure():
    """A minimal package-structure dict usable by diagram generators."""
    return {
        "package_name": "test_pkg",
        "total_functions": 3,
        "total_classes": 1,
        "module_count": 2,
        "modules": {
            "core": {
                "name": "core",
                "functions": {"func_a": {}, "func_b": {}},
                "function_count": 2,
                "classes": {"MyClass": {}},
                "class_count": 1,
                "submodules": {},
            },
            "utils": {
                "name": "utils",
                "functions": {"helper": {}},
                "function_count": 1,
                "classes": {},
                "class_count": 0,
                "submodules": {"sub1": {}},
            },
        },
    }


@pytest.fixture
def large_structure():
    """Structure with >5 functions and >3 classes to test truncation."""
    funcs = {f"fn_{i}": {} for i in range(8)}
    classes = {f"Cls_{i}": {} for i in range(5)}
    return {
        "package_name": "big_pkg",
        "total_functions": 8,
        "total_classes": 5,
        "module_count": 1,
        "modules": {
            "big_module": {
                "name": "big_module",
                "functions": funcs,
                "function_count": 8,
                "classes": classes,
                "class_count": 5,
                "submodules": {},
            }
        },
    }


SETUP_PY_CONTENT = textwrap.dedent("""\
    from setuptools import setup

    setup(
        name="my-test-package",
        version="1.2.3",
        description="A test package",
        author="Test Author",
        author_email="test@example.com",
        url="https://example.com",
        python_requires=">=3.11",
        install_requires=[
            "requests>=2.28",
            "pydantic>=2.0",
            "click",
        ],
        extras_require={
            "dev": [
                "pytest>=7.0",
                "black",
            ],
            "geo": [
                "geopandas",
            ],
        },
    )
""")


@pytest.fixture
def setup_py_file(tmp_path):
    """Write a synthetic setup.py and return its path."""
    p = tmp_path / "setup.py"
    p.write_text(SETUP_PY_CONTENT)
    return str(p)


# ----------------------------------------------------------------
# analyze_function
# ----------------------------------------------------------------

class TestAnalyzeFunction:
    def test_basic_info(self, sample_function):
        result = analyze_function(sample_function, "my_func")
        assert result["name"] == "my_func"
        assert "x" in result["signature"]
        assert "y" in result["signature"]
        assert "sample function" in result["doc"]
        assert result["module"] == __name__

    def test_long_docstring_truncated(self):
        def wordy():
            """A""" + "x" * 200

        # Manually set a long docstring
        wordy.__doc__ = "A" * 200
        result = analyze_function(wordy, "wordy")
        assert result["doc"].endswith("...")
        assert len(result["doc"]) == 103  # 100 chars + "..."

    def test_no_docstring(self):
        def no_doc():
            pass
        no_doc.__doc__ = None
        result = analyze_function(no_doc, "no_doc")
        assert result["doc"] == "No documentation"

    def test_builtin_function_error_handling(self):
        """Builtin functions may not have inspectable signatures; should not crash."""
        result = analyze_function(len, "len")
        # Should either succeed or return an error dict — never raise
        assert "name" in result


# ----------------------------------------------------------------
# analyze_class
# ----------------------------------------------------------------

class TestAnalyzeClass:
    def test_basic_info(self, sample_class):
        result = analyze_class(sample_class, "SampleClass")
        assert result["name"] == "SampleClass"
        assert "sample class" in result["doc"].lower()
        assert result["module"] == __name__

    def test_public_methods_found(self, sample_class):
        result = analyze_class(sample_class, "SampleClass")
        assert "public_method" in result["methods"]
        assert "another_method" in result["methods"]
        assert result["method_count"] == 2

    def test_private_methods_excluded(self, sample_class):
        result = analyze_class(sample_class, "SampleClass")
        assert "_private_method" not in result["methods"]

    def test_no_docstring(self):
        class Bare:
            pass
        result = analyze_class(Bare, "Bare")
        assert result["doc"] == "No documentation"

    def test_long_docstring_truncated(self):
        class Verbose:
            pass
        Verbose.__doc__ = "B" * 200
        result = analyze_class(Verbose, "Verbose")
        assert result["doc"].endswith("...")


# ----------------------------------------------------------------
# analyze_module
# ----------------------------------------------------------------

class TestAnalyzeModule:
    def test_synthetic_module(self):
        mod = types.ModuleType("synth")
        mod.__file__ = "/fake/synth.py"

        def helper():
            """Helper func."""
            pass

        class Widget:
            """Widget class."""
            pass

        mod.helper = helper
        mod.Widget = Widget
        # private should be skipped
        mod._internal = lambda: None

        result = analyze_module(mod, "synth")
        assert result["name"] == "synth"
        assert result["path"] == "/fake/synth.py"
        assert "helper" in result["functions"]
        assert result["function_count"] == 1
        assert "Widget" in result["classes"]
        assert result["class_count"] == 1

    def test_submodule_detection(self):
        parent = types.ModuleType("parent")
        parent.__file__ = "/fake/siege_utilities/parent/__init__.py"

        child = types.ModuleType("child")
        child.__file__ = "/fake/siege_utilities/parent/child.py"

        parent.child = child

        result = analyze_module(parent, "parent")
        assert "child" in result["submodules"]

    def test_foreign_submodule_excluded(self):
        parent = types.ModuleType("parent")
        parent.__file__ = "/fake/siege_utilities/parent/__init__.py"

        foreign = types.ModuleType("foreign")
        foreign.__file__ = "/usr/lib/python3/foreign.py"

        parent.foreign = foreign

        result = analyze_module(parent, "parent")
        assert "foreign" not in result["submodules"]


# ----------------------------------------------------------------
# Text diagram generation
# ----------------------------------------------------------------

class TestGenerateTextDiagram:
    def test_header(self, minimal_structure):
        text = generate_text_diagram(minimal_structure, include_details=True)
        assert "Siege Utilities Package Architecture" in text
        assert "Package: test_pkg" in text
        assert "Total Functions: 3" in text
        assert "Total Classes: 1" in text
        assert "Modules: 2" in text

    def test_module_listed(self, minimal_structure):
        text = generate_text_diagram(minimal_structure, include_details=True)
        assert "[Module] core/" in text
        assert "[Module] utils/" in text

    def test_details_included(self, minimal_structure):
        text = generate_text_diagram(minimal_structure, include_details=True)
        assert "[Functions]" in text
        assert "[Classes]" in text
        assert "[Submodules]" in text

    def test_details_excluded(self, minimal_structure):
        text = generate_text_diagram(minimal_structure, include_details=False)
        assert "[Functions]" not in text
        assert "[Classes]" not in text

    def test_truncation_functions(self, large_structure):
        text = generate_text_diagram(large_structure, include_details=True)
        assert "and 3 more" in text  # 8 functions, show first 5 → 3 more

    def test_truncation_classes(self, large_structure):
        text = generate_text_diagram(large_structure, include_details=True)
        assert "and 2 more" in text  # 5 classes, show first 3 → 2 more


# ----------------------------------------------------------------
# Markdown diagram generation
# ----------------------------------------------------------------

class TestGenerateMarkdownDiagram:
    def test_header(self, minimal_structure):
        md = generate_markdown_diagram(minimal_structure, include_details=True)
        assert "# Siege Utilities Package Architecture" in md
        assert "**Package:** test_pkg" in md

    def test_module_heading(self, minimal_structure):
        md = generate_markdown_diagram(minimal_structure, include_details=True)
        assert "## core" in md
        assert "## utils" in md

    def test_details_excluded(self, minimal_structure):
        md = generate_markdown_diagram(minimal_structure, include_details=False)
        assert "### Functions" not in md

    def test_function_truncation_at_10(self):
        funcs = {f"fn_{i}": {} for i in range(12)}
        structure = {
            "package_name": "p",
            "total_functions": 12,
            "total_classes": 0,
            "module_count": 1,
            "modules": {
                "m": {
                    "functions": funcs,
                    "function_count": 12,
                    "classes": {},
                    "class_count": 0,
                }
            },
        }
        md = generate_markdown_diagram(structure, include_details=True)
        assert "and 2 more" in md


# ----------------------------------------------------------------
# RST diagram generation
# ----------------------------------------------------------------

class TestGenerateRstDiagram:
    def test_header(self, minimal_structure):
        rst = generate_rst_diagram(minimal_structure, include_details=True)
        assert "Siege Utilities Package Architecture" in rst
        assert "=" * 50 in rst

    def test_module_underline(self, minimal_structure):
        rst = generate_rst_diagram(minimal_structure, include_details=True)
        assert "core" in rst
        assert "-" * len("core") in rst

    def test_details_excluded(self, minimal_structure):
        rst = generate_rst_diagram(minimal_structure, include_details=False)
        # The header contains "Total Functions" — check that per-module detail lines are absent
        assert "Functions (2):" not in rst
        assert "Classes (1):" not in rst


# ----------------------------------------------------------------
# generate_architecture_diagram (orchestrator)
# ----------------------------------------------------------------

class TestGenerateArchitectureDiagram:
    @patch("siege_utilities.development.architecture.analyze_package_structure")
    def test_text_format(self, mock_aps, minimal_structure):
        mock_aps.return_value = minimal_structure
        result = generate_architecture_diagram(output_format="text")
        assert "Siege Utilities Package Architecture" in result

    @patch("siege_utilities.development.architecture.analyze_package_structure")
    def test_json_format(self, mock_aps, minimal_structure):
        mock_aps.return_value = minimal_structure
        result = generate_architecture_diagram(output_format="json")
        parsed = json.loads(result)
        assert parsed["package_name"] == "test_pkg"

    @patch("siege_utilities.development.architecture.analyze_package_structure")
    def test_markdown_format(self, mock_aps, minimal_structure):
        mock_aps.return_value = minimal_structure
        result = generate_architecture_diagram(output_format="markdown")
        assert "# Siege Utilities Package Architecture" in result

    @patch("siege_utilities.development.architecture.analyze_package_structure")
    def test_rst_format(self, mock_aps, minimal_structure):
        mock_aps.return_value = minimal_structure
        result = generate_architecture_diagram(output_format="rst")
        assert "=" * 50 in result

    @patch("siege_utilities.development.architecture.analyze_package_structure")
    def test_unsupported_format(self, mock_aps, minimal_structure):
        mock_aps.return_value = minimal_structure
        result = generate_architecture_diagram(output_format="html")
        assert "Unsupported output format" in result

    @patch("siege_utilities.development.architecture.analyze_package_structure")
    def test_error_in_structure(self, mock_aps):
        mock_aps.return_value = {"error": "boom"}
        result = generate_architecture_diagram()
        assert "Error: boom" in result

    @patch("siege_utilities.development.architecture.analyze_package_structure")
    def test_output_file_written(self, mock_aps, minimal_structure, tmp_path):
        mock_aps.return_value = minimal_structure
        out = str(tmp_path / "diagram.txt")
        result = generate_architecture_diagram(output_format="text", output_file=out)
        assert Path(out).exists()
        assert Path(out).read_text() == result

    @patch("siege_utilities.development.architecture.analyze_package_structure")
    def test_output_file_bad_path(self, mock_aps, minimal_structure):
        mock_aps.return_value = minimal_structure
        # Should not raise, just log warning
        result = generate_architecture_diagram(
            output_format="text",
            output_file="/nonexistent_dir_xyz/file.txt",
        )
        assert len(result) > 0  # diagram still returned

    @patch("siege_utilities.development.architecture.analyze_package_structure")
    def test_include_details_false(self, mock_aps, minimal_structure):
        mock_aps.return_value = minimal_structure
        result = generate_architecture_diagram(output_format="text", include_details=False)
        assert "[Functions]" not in result


# ----------------------------------------------------------------
# analyze_package_structure
# ----------------------------------------------------------------

class TestAnalyzePackageStructure:
    def test_nonexistent_package(self):
        result = analyze_package_structure("totally_nonexistent_package_xyz")
        assert "error" in result

    @patch("siege_utilities.development.architecture.importlib.import_module")
    def test_generic_exception(self, mock_import):
        mock_import.side_effect = RuntimeError("kaboom")
        result = analyze_package_structure("boom_pkg")
        assert "error" in result
        assert "kaboom" in result["error"]

    @patch("siege_utilities.development.architecture.importlib.import_module")
    def test_synthetic_package(self, mock_import):
        """Build a tiny synthetic package and verify structure dict."""
        pkg = types.ModuleType("fakepkg")
        pkg.__file__ = "/fake/fakepkg/__init__.py"

        sub = types.ModuleType("fakepkg.sub")
        sub.__file__ = "/fake/fakepkg/sub.py"

        def greet():
            """Say hi."""
            pass

        sub.greet = greet
        pkg.sub = sub

        mock_import.return_value = pkg

        result = analyze_package_structure("fakepkg")
        assert result["package_name"] == "fakepkg"
        assert result["module_count"] == 1
        assert "sub" in result["modules"]
        assert result["total_functions"] >= 1


# ----------------------------------------------------------------
# generate_requirements_txt
# ----------------------------------------------------------------

class TestGenerateRequirementsTxt:
    def test_success(self, setup_py_file, tmp_path):
        out = str(tmp_path / "req.txt")
        assert generate_requirements_txt(setup_py_file, out) is True
        content = Path(out).read_text()
        assert "requests>=2.28" in content
        assert "pydantic>=2.0" in content
        assert "click" in content
        # extras should NOT appear
        assert "pytest" not in content

    def test_missing_setup_py(self, tmp_path):
        result = generate_requirements_txt(str(tmp_path / "nope.py"))
        assert result is False

    def test_empty_setup_py(self, tmp_path):
        empty = tmp_path / "setup.py"
        empty.write_text("from setuptools import setup\nsetup()\n")
        out = str(tmp_path / "req.txt")
        assert generate_requirements_txt(str(empty), out) is True
        assert Path(out).read_text() == ""


# ----------------------------------------------------------------
# generate_pyproject_toml
# ----------------------------------------------------------------

class TestGeneratePyprojectToml:
    def test_success(self, setup_py_file, tmp_path):
        out = str(tmp_path / "pyproject.toml")
        assert generate_pyproject_toml(setup_py_file, out) is True
        content = Path(out).read_text()
        assert 'name = "my-test-package"' in content
        assert 'version = "1.2.3"' in content
        assert '"requests>=2.28"' in content
        assert "setuptools" in content  # build backend
        assert "[project.optional-dependencies]" in content
        assert 'Homepage = "https://example.com"' in content
        assert 'requires-python = ">=3.11"' in content

    def test_missing_setup_py(self, tmp_path):
        assert generate_pyproject_toml(str(tmp_path / "nope.py")) is False

    def test_minimal_setup_py(self, tmp_path):
        p = tmp_path / "setup.py"
        p.write_text("from setuptools import setup\nsetup()\n")
        out = str(tmp_path / "pyproject.toml")
        assert generate_pyproject_toml(str(p), out) is True
        content = Path(out).read_text()
        assert 'name = "unknown-package"' in content
        assert 'version = "0.1.0"' in content


# ----------------------------------------------------------------
# generate_poetry_toml
# ----------------------------------------------------------------

class TestGeneratePoetryToml:
    def test_success(self, setup_py_file, tmp_path):
        out = str(tmp_path / "pyproject.toml")
        assert generate_poetry_toml(setup_py_file, out) is True
        content = Path(out).read_text()
        assert "[tool.poetry]" in content
        assert 'name = "my-test-package"' in content
        assert "poetry-core" in content
        assert "poetry.core.masonry.api" in content
        assert "[tool.poetry.dependencies]" in content

    def test_dev_extras_placed_correctly(self, setup_py_file, tmp_path):
        out = str(tmp_path / "pyproject.toml")
        generate_poetry_toml(setup_py_file, out)
        content = Path(out).read_text()
        assert "[tool.poetry.group.dev.dependencies]" in content
        assert "pytest" in content

    def test_url_section(self, setup_py_file, tmp_path):
        out = str(tmp_path / "pyproject.toml")
        generate_poetry_toml(setup_py_file, out)
        content = Path(out).read_text()
        assert "[tool.poetry.urls]" in content
        assert "https://example.com" in content

    def test_missing_setup_py(self, tmp_path):
        assert generate_poetry_toml(str(tmp_path / "nope.py")) is False


# ----------------------------------------------------------------
# generate_uv_toml
# ----------------------------------------------------------------

class TestGenerateUvToml:
    def test_delegates_to_pyproject(self, setup_py_file, tmp_path):
        out = str(tmp_path / "pyproject.toml")
        assert generate_uv_toml(setup_py_file, out) is True
        content = Path(out).read_text()
        # UV uses standard PEP 621 format — same as generate_pyproject_toml
        assert "[project]" in content
        assert "setuptools" in content

    def test_missing_setup_py(self, tmp_path):
        assert generate_uv_toml(str(tmp_path / "nope.py")) is False
