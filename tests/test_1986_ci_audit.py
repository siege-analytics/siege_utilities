"""CI workflow shape after the #1986 audit.

Every ``scripts/check_*.py`` guard is either run by a workflow or listed as a
local-only tool in ``scripts/README.md``; the battle-test job runs on manual
runs only; and no CI step is a lint run that cannot fail.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CI = yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))
CHECK_SCRIPT_RE = re.compile(r"scripts/(check_[a-z0-9_]+\.py)")


def _ci_triggers() -> dict:
    # PyYAML reads the bare key `on` as True.
    return CI.get("on", CI.get(True))


def _workflow_run_text() -> str:
    runs = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        for job in (data.get("jobs") or {}).values():
            runs.extend(step.get("run", "") for step in job.get("steps") or [])
    return "\n".join(runs)


def _readme_local_only_section() -> str:
    readme = (ROOT / "scripts" / "README.md").read_text(encoding="utf-8")
    match = re.search(r"^### Local-only tools\n(.*?)(?=^#{2,3} )", readme, re.MULTILINE | re.DOTALL)
    assert match, "scripts/README.md has no '### Local-only tools' section"
    return match.group(1)


def test_every_check_script_is_run_by_ci_or_documented_local_only() -> None:
    scripts = {path.name for path in (ROOT / "scripts").glob("check_*.py")}
    run_by_ci = set(CHECK_SCRIPT_RE.findall(_workflow_run_text()))
    local_only = set(CHECK_SCRIPT_RE.findall(_readme_local_only_section()))
    assert scripts, "no scripts/check_*.py found"
    assert not (run_by_ci & local_only), f"listed local-only but run by CI: {sorted(run_by_ci & local_only)}"
    assert scripts <= run_by_ci | local_only, f"neither run by CI nor local-only: {sorted(scripts - run_by_ci - local_only)}"
    assert local_only <= scripts, f"local-only entries with no script: {sorted(local_only - scripts)}"


def test_static_guards_run_the_credential_url_guard_as_a_failing_step() -> None:
    steps = {step.get("run", ""): step for step in CI["jobs"]["static-guards"]["steps"]}
    credential = steps["python scripts/check_credential_urls.py"]
    assert "continue-on-error" not in credential
    assert credential["if"] == "${{ !cancelled() }}"


def test_advisory_steps_are_named_advisory() -> None:
    for job_name, job in CI["jobs"].items():
        for step in job.get("steps") or []:
            if step.get("continue-on-error") is True:
                assert "advisory" in step.get("name", ""), f"{job_name}: {step.get('name')!r} can never fail but is not named advisory"


def test_griffe_job_is_named_advisory_without_stale_ratchet_text() -> None:
    job = CI["jobs"]["griffe-api-diff"]
    assert "advisory" in job["name"]
    step = next(step for step in job["steps"] if "griffe check" in step.get("run", ""))
    assert "advisory" in step["name"]
    ci_text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert "api-contract-regression" not in ci_text
    assert "release cycle" not in ci_text


def test_battle_test_runs_on_manual_runs_only() -> None:
    triggers = _ci_triggers()
    assert "workflow_dispatch" in triggers
    job = CI["jobs"]["battle-test"]
    assert job["if"] == "github.event_name == 'workflow_dispatch'"


def test_no_lint_step_exits_zero_regardless_of_findings() -> None:
    assert "--exit-zero" not in _workflow_run_text()
