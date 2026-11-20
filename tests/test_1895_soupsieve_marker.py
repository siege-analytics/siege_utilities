"""soupsieve floor and dependency-audit target stay in step (#1895).

The geo, web and all extras require soupsieve>=4.0.0 (the CVE-2026-126190
fix) only on Python 3.11.5 and newer, because soupsieve 4.0 and 4.1 cannot
install on earlier 3.11 patch releases. CI audits the resolution at that
marker floor and must not ignore the advisory. A green audit does not
exercise the marker itself, so these checks pin the declarations.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads(
    (ROOT / "pyproject.toml").read_text(encoding="utf-8")
)
WORKFLOWS = ROOT / ".github" / "workflows"
CI_WORKFLOW = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")

MARKER_FLOOR = "3.11.5"
SOUPSIEVE_SPEC = (
    f"soupsieve>=4.0.0; python_full_version >= '{MARKER_FLOOR}'"
)
SOUPSIEVE_ADVISORY_IDS = ("CVE-2026-126190", "GHSA-mmhr-3c5m-f64f")
AUDIT_COMPILE = re.compile(
    r"uv pip compile pyproject\.toml --extra all --extra dev "
    r"--python-version (\S+) -o (\S+)"
)
# Matches "--ignore-vuln ID", "--ignore-vuln=ID" and a backslash-continued
# "--ignore-vuln \<newline> ID".
IGNORE_VULN = re.compile(r"--ignore-vuln(?:\s|=|\\)+([A-Za-z0-9._:-]+)")


def _audit_targets() -> dict[str, str]:
    """Map each audited requirements file to its resolution version."""
    return {
        output: version
        for version, output in AUDIT_COMPILE.findall(CI_WORKFLOW)
    }


@pytest.mark.parametrize("extra", ["geo", "web", "all"])
def test_extra_carries_marker_scoped_soupsieve_floor(extra):
    deps = PYPROJECT["project"]["optional-dependencies"][extra]
    assert "beautifulsoup4>=4.12.0" in deps
    assert SOUPSIEVE_SPEC in deps


def test_marker_floor_does_not_raise_requires_python():
    assert PYPROJECT["project"]["requires-python"] == ">=3.11"


def test_audit_resolves_at_the_marker_floor_only():
    assert CI_WORKFLOW.count("uv pip compile") == 1
    assert _audit_targets() == {"security-requirements.txt": MARKER_FLOOR}


@pytest.mark.parametrize(
    "workflow", sorted(WORKFLOWS.glob("*.yml")), ids=lambda p: p.name
)
def test_soupsieve_advisory_is_never_ignored(workflow):
    text = workflow.read_text(encoding="utf-8")
    ignored = set(IGNORE_VULN.findall(text))
    assert ignored.isdisjoint(SOUPSIEVE_ADVISORY_IDS)


def test_ignore_pattern_catches_every_spelling():
    spellings = (
        "--ignore-vuln CVE-2026-126190",
        "--ignore-vuln=CVE-2026-126190",
        "--ignore-vuln \\\n          CVE-2026-126190",
    )
    for spelling in spellings:
        assert IGNORE_VULN.findall(spelling) == ["CVE-2026-126190"]
