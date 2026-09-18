"""Root-import contracts for package-introspection helpers.

Covers three documented-but-untested public symbols that reflect on the
installed siege_utilities package and the running interpreter:

- analyze_package_structure (development.architecture)
- generate_architecture_diagram (development.architecture)
- diagnose_environment (runtime)

These are pure, read-only helpers; the tests exercise the real package
rather than a mock so the assertions verify the documented contract.
"""

import json
import sys
import types

from siege_utilities import analyze_package_structure
from siege_utilities import generate_architecture_diagram
from siege_utilities import diagnose_environment
from siege_utilities.development.architecture import analyze_module


class TestAnalyzePackageStructure:
    def test_reports_real_package_shape(self):
        structure = analyze_package_structure()
        assert structure["package_name"] == "siege_utilities"
        assert structure["package_path"].endswith("siege_utilities")
        # A populated package: at least one module, and functions discovered.
        assert structure["module_count"] > 0
        assert structure["total_functions"] > 0
        assert isinstance(structure["modules"], dict)
        assert isinstance(structure["functions"], dict)
        assert isinstance(structure["classes"], dict)

    def test_unknown_package_reports_error_not_raises(self):
        structure = analyze_package_structure("no_such_package_xyz_123")
        assert "error" in structure
        assert "no_such_package_xyz_123" in structure["error"]

    def test_analyze_module_breaks_reference_cycles(self):
        # Regression: analyze_module recursed into every submodule with no
        # visited set, so a cyclic module graph (siege_utilities submodules
        # re-export one another) raised RecursionError once enough of the
        # package was imported. A synthetic a <-> b cycle must terminate.
        mod_a = types.ModuleType("siege_utilities._cycle_a")
        mod_a.__file__ = "/pkg/siege_utilities/_cycle_a.py"
        mod_b = types.ModuleType("siege_utilities._cycle_b")
        mod_b.__file__ = "/pkg/siege_utilities/_cycle_b.py"
        mod_a.b = mod_b
        mod_b.a = mod_a

        result = analyze_module(mod_a, "a")
        assert "b" in result["submodules"]
        # The edge back to 'a' is recorded as a broken cycle, not recursed.
        back = result["submodules"]["b"]["submodules"]["a"]
        assert back.get("note") == "already analyzed (cycle avoided)"


class TestGenerateArchitectureDiagram:
    def test_text_format_has_header_and_counts(self):
        diagram = generate_architecture_diagram(output_format="text")
        assert "Siege Utilities Package Architecture" in diagram
        assert "Total Functions:" in diagram

    def test_json_format_is_valid_json(self):
        diagram = generate_architecture_diagram(output_format="json")
        parsed = json.loads(diagram)
        assert parsed["package_name"] == "siege_utilities"

    def test_markdown_format_uses_markdown_heading(self):
        diagram = generate_architecture_diagram(output_format="markdown")
        assert diagram.startswith("# Siege Utilities Package Architecture")

    def test_rst_format_has_underline(self):
        diagram = generate_architecture_diagram(output_format="rst")
        assert "Siege Utilities Package Architecture" in diagram
        assert "=" * 50 in diagram

    def test_unsupported_format_returns_message(self):
        diagram = generate_architecture_diagram(output_format="bogus")
        assert diagram == "Unsupported output format: bogus"

    def test_output_file_is_written(self, tmp_path):
        out = tmp_path / "arch.txt"
        diagram = generate_architecture_diagram(
            output_format="text", output_file=str(out)
        )
        assert out.exists()
        assert out.read_text(encoding="utf-8") == diagram


class TestDiagnoseEnvironment:
    def test_reports_documented_keys_with_types(self):
        diag = diagnose_environment()
        # Documented keys.
        for key in (
            "python_version",
            "platform",
            "is_databricks",
            "pydantic_version",
            "pydantic_v2",
            "siege_utilities_version",
            "stale_pydantic_modules",
        ):
            assert key in diag, f"missing diagnostic key: {key}"
        # Types match the documented contract.
        assert isinstance(diag["is_databricks"], bool)
        assert isinstance(diag["pydantic_v2"], bool)
        assert isinstance(diag["stale_pydantic_modules"], list)
        # python_version reflects the running interpreter.
        expected = (
            f"{sys.version_info.major}."
            f"{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )
        assert diag["python_version"] == expected
        assert diag["platform"] == sys.platform
