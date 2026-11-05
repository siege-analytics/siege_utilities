"""Packaging regressions for optional CRM dependencies (#1449)."""

import ast
import sys
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

REPO_ROOT = Path(__file__).resolve().parents[1]


def _project() -> dict:
    return tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]


def test_msal_is_declared_in_an_extra_with_a_lower_bound():
    requirements = [
        Requirement(spec)
        for specs in _project()["optional-dependencies"].values()
        for spec in specs
        if canonicalize_name(Requirement(spec).name) == "msal"
    ]
    assert requirements, "msal is missing from every pyproject.toml extra"
    for requirement in requirements:
        assert any(
            spec.operator in {">=", ">", "~="} for spec in requirement.specifier
        ), f"{requirement} must declare a lower version bound"


def test_crm_extra_is_complete_and_included_in_all():
    extras = _project()["optional-dependencies"]
    crm = extras["crm"]
    assert {"msal", "pandas"} <= {
        canonicalize_name(Requirement(spec).name) for spec in crm
    }
    assert set(crm) <= set(extras["all"])


def test_connector_non_core_imports_are_declared_in_extras():
    project = _project()
    core = {
        canonicalize_name(Requirement(spec).name)
        for spec in project["dependencies"]
    }
    optional = {
        canonicalize_name(Requirement(spec).name)
        for specs in project["optional-dependencies"].values()
        for spec in specs
    }
    # CRM imports currently share their distribution names. Core requests
    # and pydantic need no extra; pandas and msal do. Inspect source so this
    # contract also runs when optional dependencies are not installed.
    for path in sorted((REPO_ROOT / "siege_utilities" / "connectors").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports.add(node.module.split(".")[0])
        for name in imports - sys.stdlib_module_names - {"siege_utilities"}:
            dependency = canonicalize_name(name)
            if dependency not in core:
                assert dependency in optional, (
                    f"{path.name} imports {name}, but no extra declares it"
                )


@pytest.mark.parametrize("missing", ["MSAL_AVAILABLE", "REQUESTS_AVAILABLE"])
def test_dynamics_missing_dependency_names_crm_extra(monkeypatch, missing):
    pytest.importorskip("pandas")
    import siege_utilities.connectors.dynamics as dynamics

    monkeypatch.setattr(dynamics, "REQUESTS_AVAILABLE", True)
    monkeypatch.setattr(dynamics, "MSAL_AVAILABLE", True)
    monkeypatch.setattr(dynamics, missing, False)
    with pytest.raises(ImportError, match=r"pip install siege-utilities\[crm\]"):
        dynamics.DynamicsConnector(
            environment_url="https://example.crm.dynamics.com",
            tenant_id="tenant",
            client_id="client",
        )
