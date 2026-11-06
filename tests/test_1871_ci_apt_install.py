"""CI package installs must not let an apt mirror stall consume the job (#1871).

``scripts/ci_apt_install.sh`` is run with stub ``sudo`` and ``apt-get`` on an
allow-listed PATH and the real ``timeout``. The stub follows a per-call plan
(``ok``, ``fail`` or ``hang``) so stalls, failures and retries are exercised
without network access. A guard then checks every workflow step.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "ci_apt_install.sh"
WORKFLOWS = REPO / ".github" / "workflows"
PACKAGES = ["gdal-bin", "libgdal-dev", "libgeos-dev", "libproj-dev"]
APT_OPTIONS = [
    "-o", "Acquire::Retries=3",
    "-o", "Acquire::http::Timeout=30",
    "-o", "Acquire::https::Timeout=30",
]
# Script defaults: 5 bounded commands (update + install, then dpkg --configure
# + update + install), each up to 120 s plus a 30 s kill-after, and a 10 s delay.
WORST_CASE_SECONDS = 5 * (120 + 30) + 10


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def run_script(
    tmp_path: Path, plan: list[str], *packages: str, dpkg_exit: int = 0,
) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
    timeout_bin = shutil.which("timeout")
    if timeout_bin is None:
        pytest.skip("GNU timeout is required to exercise the stall handling")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "timeout").symlink_to(timeout_bin)
    for tool in ("sleep",):
        executable = shutil.which(tool)
        assert executable is not None, tool
        (bin_dir / tool).symlink_to(executable)
    _write_executable(bin_dir / "sudo", '#!/bin/bash\nexec "$@"\n')

    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    calls_file = tmp_path / "calls.jsonl"
    _write_executable(
        bin_dir / "apt-get",
        f"#!{sys.executable}\n"
        "import json, os, sys, time\n"
        "plan_path = os.environ['APT_STUB_PLAN']\n"
        "plan = json.load(open(plan_path))\n"
        "action = plan.pop(0) if plan else 'ok'\n"
        "json.dump(plan, open(plan_path, 'w'))\n"
        "with open(os.environ['APT_STUB_CALLS'], 'a') as log:\n"
        "    log.write(json.dumps(['apt-get', *sys.argv[1:]]) + '\\n')\n"
        "if action == 'hang':\n"
        "    time.sleep(60)\n"
        "sys.exit(0 if action == 'ok' else 100)\n",
    )
    _write_executable(
        bin_dir / "dpkg",
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "with open(os.environ['APT_STUB_CALLS'], 'a') as log:\n"
        "    log.write(json.dumps(['dpkg', *sys.argv[1:]]) + '\\n')\n"
        "sys.exit(int(os.environ['DPKG_STUB_EXIT']))\n",
    )

    result = subprocess.run(
        ["/bin/bash", str(SCRIPT), *packages],
        env={
            "PATH": str(bin_dir),
            "APT_STUB_PLAN": str(plan_file),
            "APT_STUB_CALLS": str(calls_file),
            "APT_ATTEMPT_TIMEOUT": "1",
            "APT_RETRY_DELAY": "0",
            "DPKG_STUB_EXIT": str(dpkg_exit),
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    calls = []
    if calls_file.exists():
        calls = [json.loads(line) for line in calls_file.read_text(encoding="utf-8").splitlines()]
    return result, calls


def _update() -> list[str]:
    return ["apt-get", *APT_OPTIONS, "update"]


def _install() -> list[str]:
    return ["apt-get", *APT_OPTIONS, "install", "-y", "--no-install-recommends", *PACKAGES]


def _repair() -> list[str]:
    return ["dpkg", "--configure", "-a"]


def test_successful_install_uses_bounded_apt_options(tmp_path: Path) -> None:
    result, calls = run_script(tmp_path, ["ok", "ok"], *PACKAGES)

    assert result.returncode == 0, result.stdout + result.stderr
    # A first attempt has nothing to repair, so dpkg is not run.
    assert calls == [_update(), _install()]
    assert "succeeded on attempt 1" in result.stdout


def test_stalled_update_is_cut_off_and_retried(tmp_path: Path) -> None:
    result, calls = run_script(tmp_path, ["hang", "ok", "ok"], *PACKAGES)

    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [_update(), _repair(), _update(), _install()]
    # timeout(1) reports 124 when it stopped the stalled apt-get.
    assert "attempt 1 failed or stalled (exit 124)" in result.stderr
    assert "succeeded on attempt 2" in result.stdout


def test_killed_install_repairs_dpkg_before_the_retry(tmp_path: Path) -> None:
    # The first install is stopped mid-run (exit 124), as it would be during
    # dpkg unpack/configure; the retry must run `dpkg --configure -a` before
    # `apt-get update`, or it fails at once on "dpkg was interrupted".
    result, calls = run_script(tmp_path, ["ok", "hang", "ok", "ok"], *PACKAGES)

    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [_update(), _install(), _repair(), _update(), _install()]
    assert "attempt 1 failed or stalled (exit 124)" in result.stderr


def test_failed_dpkg_repair_is_reported_and_the_retry_still_runs(tmp_path: Path) -> None:
    result, calls = run_script(tmp_path, ["ok", "hang", "ok", "ok"], *PACKAGES, dpkg_exit=1)

    assert result.returncode == 0, result.stdout + result.stderr
    assert calls == [_update(), _install(), _repair(), _update(), _install()]
    assert "warning: dpkg --configure -a did not complete before attempt 2" in result.stderr


def test_two_failed_attempts_fail_the_step(tmp_path: Path) -> None:
    result, calls = run_script(tmp_path, ["ok", "fail", "ok", "fail"], *PACKAGES)

    assert result.returncode == 1, result.stdout + result.stderr
    assert calls == [_update(), _install(), _repair(), _update(), _install()]
    assert "apt install failed after 2 attempts" in result.stderr


def test_missing_packages_is_a_usage_error(tmp_path: Path) -> None:
    result, calls = run_script(tmp_path, [])

    assert result.returncode == 2
    assert calls == []


def _workflow_steps() -> list[tuple[str, str, dict[str, Any], dict[str, Any]]]:
    steps = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        for job_name, job in (data.get("jobs") or {}).items():
            for step in job.get("steps") or []:
                steps.append((workflow.name, job_name, job, step))
    return steps


def test_no_workflow_step_runs_apt_get_directly() -> None:
    direct = [
        f"{workflow}:{job}:{step.get('name', '?')}"
        for workflow, job, _, step in _workflow_steps()
        if "apt-get" in str(step.get("run", ""))
    ]
    assert direct == [], f"use scripts/ci_apt_install.sh instead of apt-get: {direct}"


def test_apt_install_steps_have_a_step_timeout_inside_the_job_budget() -> None:
    install_steps = [
        (workflow, job_name, job, step)
        for workflow, job_name, job, step in _workflow_steps()
        if "scripts/ci_apt_install.sh" in str(step.get("run", ""))
    ]
    assert install_steps, "expected workflow steps that install packages through the script"
    for workflow, job_name, job, step in install_steps:
        where = f"{workflow}:{job_name}"
        step_timeout = step.get("timeout-minutes")
        assert isinstance(step_timeout, int), f"{where}: install step needs timeout-minutes"
        assert step_timeout * 60 > WORST_CASE_SECONDS, f"{where}: step timeout shorter than two attempts"
        job_timeout = job.get("timeout-minutes")
        if job_timeout is not None:
            assert step_timeout < job_timeout, f"{where}: step timeout must be below the job timeout"
