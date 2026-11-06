"""CI package installs must survive a slow or stalled apt mirror (#1871).

``scripts/ci_apt_install.sh`` is run with stub ``sudo``, ``apt-get`` and
``dpkg`` on an allow-listed PATH and the real ``timeout``. The ``apt-get`` stub
reads the mirror the runner would use from a fixture ``apt-mirrors.txt`` and
"downloads" by creating ``<package>.deb`` in a fixture archive directory.
Behaviour is set by rules, not by call order, so a stub that ``timeout``
stops before it starts cannot shift the scenario:

- ``APT_STUB_HANG_MIRROR``: ``update`` and ``download`` hang on this mirror;
- ``APT_STUB_SLOW``: these commands make steady progress for
  ``APT_STUB_SLOW_SECONDS``, longer than the first-attempt cap;
- ``APT_STUB_FAIL``: these commands exit 100;
- ``APT_STUB_BEFORE_REPAIR`` (``command:action``): applies until
  ``dpkg --configure -a`` has exited 0, that is, on the first attempt.

Guards then check every workflow step and the ``apt-install`` action.
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
ACTION = REPO / ".github" / "actions" / "apt-install" / "action.yml"
ACTION_REF = "./.github/actions/apt-install"
PACKAGES = ["gdal-bin", "libgdal-dev", "libgeos-dev", "libproj-dev"]
APT_OPTIONS = [
    "-o", "Acquire::Retries=3",
    "-o", "Acquire::http::Timeout=30",
    "-o", "Acquire::https::Timeout=30",
    "-o", "APT::Keep-Downloaded-Packages=true",
]
PRIMARY = "azure.archive.ubuntu.com"
FALLBACK = "archive.ubuntu.com"
# Caps used by the tests. They sit well above stub start-up time, so only
# the hanging or slow stubs reach them.
CAP_SECONDS = "5"
SLOW_SECONDS = "8"
# /etc/apt/apt-mirrors.txt as actions/runner-images writes it (144 bytes).
RUNNER_MIRRORS = (
    "http://azure.archive.ubuntu.com/ubuntu/\tpriority:1\n"
    "https://archive.ubuntu.com/ubuntu/\tpriority:2\n"
    "https://security.ubuntu.com/ubuntu/\tpriority:3\n"
)
UBUNTU_SOURCES = (
    "Types: deb\n"
    "URIs: mirror+file:/etc/apt/apt-mirrors.txt\n"
    "Suites: noble noble-updates noble-backports noble-security\n"
    "Components: main universe restricted multiverse\n"
)
MICROSOFT_LIST = "deb [arch=amd64,arm64] https://packages.microsoft.com/ubuntu/24.04/prod noble main\n"
DIRECT_LIST = "deb http://azure.archive.ubuntu.com/ubuntu/ noble main universe\n"

APT_STUB = """\
import json, os, sys, time

args = sys.argv[1:]
words = [a for i, a in enumerate(args) if a != '-o' and (i == 0 or args[i - 1] != '-o')]
command = words[0]
if command == 'install' and '--download-only' in words:
    command = 'download'
packages = [w for w in words[1:] if not w.startswith('-')]
archives = os.environ['APT_ARCHIVES_DIR']
entry = {'cmd': command, 'argv': args}
if command in ('update', 'download'):
    with open(os.path.join(os.environ['APT_CONFIG_DIR'], 'apt-mirrors.txt')) as handle:
        entry['mirror'] = handle.readline().split('//', 1)[1].split('/', 1)[0]
if command == 'download':
    entry['fetch'] = [p for p in packages if not os.path.exists(os.path.join(archives, p + '.deb'))]

action = 'ok'
if command in os.environ.get('APT_STUB_FAIL', '').split(','):
    action = 'fail'
if command in os.environ.get('APT_STUB_SLOW', '').split(','):
    action = 'slow'
if entry.get('mirror') and entry['mirror'] == os.environ.get('APT_STUB_HANG_MIRROR'):
    action = 'hang'
rule = os.environ.get('APT_STUB_BEFORE_REPAIR', '')
if rule and rule.split(':')[0] == command and not os.path.exists(os.environ['APT_STUB_REPAIRED']):
    action = rule.split(':')[1]
entry['action'] = action
with open(os.environ['APT_STUB_CALLS'], 'a') as log:
    log.write(json.dumps(entry) + '\\n')

if action == 'hang':
    time.sleep(60)
elif action == 'slow':
    # A live transfer: steady progress, but longer than the first-attempt cap.
    deadline = time.monotonic() + float(os.environ['APT_STUB_SLOW_SECONDS'])
    while time.monotonic() < deadline:
        print('Get: progress', flush=True)
        time.sleep(0.2)
if action == 'fail':
    sys.exit(100)
if command == 'download':
    for package in entry['fetch']:
        with open(os.path.join(archives, package + '.deb'), 'w') as handle:
            handle.write(package)
if command == 'install':
    absent = [p for p in packages if not os.path.exists(os.path.join(archives, p + '.deb'))]
    sys.exit(100 if absent else 0)
"""

DPKG_STUB = """\
import json, os, sys
with open(os.environ['APT_STUB_CALLS'], 'a') as log:
    log.write(json.dumps({'cmd': 'dpkg', 'argv': sys.argv[1:]}) + '\\n')
status = int(os.environ['DPKG_STUB_EXIT'])
if status == 0 and sys.argv[1:] == ['--configure', '-a']:
    open(os.environ['APT_STUB_REPAIRED'], 'w').close()
sys.exit(status)
"""


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


class Runner:
    """Fixture apt layout plus stubs; ``run`` executes the real script."""

    def __init__(self, tmp_path: Path) -> None:
        timeout_bin = shutil.which("timeout")
        if timeout_bin is None:
            pytest.skip("GNU timeout is required to exercise the stall handling")
        self.tmp = tmp_path
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        (self.bin / "timeout").symlink_to(timeout_bin)
        for tool in ("sleep", "sed", "grep", "cp", "rm", "mkdir", "mktemp"):
            executable = shutil.which(tool)
            assert executable is not None, tool
            (self.bin / tool).symlink_to(executable)
        _write_executable(self.bin / "sudo", '#!/bin/bash\nexec "$@"\n')
        _write_executable(self.bin / "apt-get", f"#!{sys.executable}\n{APT_STUB}")
        _write_executable(self.bin / "dpkg", f"#!{sys.executable}\n{DPKG_STUB}")

        self.config = tmp_path / "etc-apt"
        (self.config / "sources.list.d").mkdir(parents=True)
        (self.config / "apt-mirrors.txt").write_text(RUNNER_MIRRORS, encoding="utf-8")
        (self.config / "sources.list.d" / "ubuntu.sources").write_text(UBUNTU_SOURCES, encoding="utf-8")
        (self.config / "sources.list.d" / "microsoft-prod.list").write_text(MICROSOFT_LIST, encoding="utf-8")
        self.archives = tmp_path / "archives"
        self.archives.mkdir()
        self.cache = tmp_path / "cache"
        self.output = tmp_path / "github_output"
        self.output.touch()
        self.calls_file = tmp_path / "calls.jsonl"

    def run(
        self,
        *packages: str,
        use_cache: bool = True,
        dpkg_exit: int = 0,
        **env: str,
    ) -> subprocess.CompletedProcess[str]:
        environment = {
            "PATH": str(self.bin),
            "APT_STUB_CALLS": str(self.calls_file),
            "APT_STUB_REPAIRED": str(self.tmp / "repaired"),
            "APT_STUB_SLOW_SECONDS": SLOW_SECONDS,
            "APT_CONFIG_DIR": str(self.config),
            "APT_ARCHIVES_DIR": str(self.archives),
            "APT_ATTEMPT_TIMEOUT": CAP_SECONDS,
            "APT_DPKG_TIMEOUT": CAP_SECONDS,
            "APT_RETRY_DELAY": "0",
            "DPKG_STUB_EXIT": str(dpkg_exit),
            "GITHUB_OUTPUT": str(self.output),
            **env,
        }
        if use_cache:
            environment["APT_ARCHIVE_CACHE_DIR"] = str(self.cache)
        return subprocess.run(
            ["/bin/bash", str(SCRIPT), *packages],
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
        )

    @property
    def calls(self) -> list[dict[str, Any]]:
        if not self.calls_file.exists():
            return []
        lines = self.calls_file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    @property
    def commands(self) -> list[str]:
        return [call["cmd"] for call in self.calls]

    def mirrors(self) -> list[str]:
        return [call["mirror"] for call in self.calls if "mirror" in call]


def _debs(directory: Path) -> list[str]:
    return sorted(path.stem for path in directory.glob("*.deb"))


def test_successful_install_uses_bounded_apt_options(tmp_path: Path) -> None:
    runner = Runner(tmp_path)
    result = runner.run(*PACKAGES, use_cache=False)

    assert result.returncode == 0, result.stdout + result.stderr
    # A first attempt has nothing to repair and stays on the primary mirror.
    assert runner.commands == ["update", "download", "install"]
    for call in runner.calls:
        assert call["argv"][: len(APT_OPTIONS)] == APT_OPTIONS
    download, install = runner.calls[1], runner.calls[2]
    assert download["argv"][len(APT_OPTIONS):] == [
        "install", "-y", "--no-install-recommends", "--download-only", *PACKAGES,
    ]
    assert install["argv"][len(APT_OPTIONS):] == ["install", "-y", "--no-install-recommends", *PACKAGES]
    assert runner.mirrors() == [PRIMARY, PRIMARY]
    assert "succeeded on attempt 1" in result.stdout
    # Without a cache directory nothing is staged for saving.
    assert runner.output.read_text(encoding="utf-8") == ""


def test_cache_hit_installs_without_downloading(tmp_path: Path) -> None:
    runner = Runner(tmp_path)
    runner.cache.mkdir()
    for package in PACKAGES:
        (runner.cache / f"{package}.deb").write_text(package, encoding="utf-8")

    result = runner.run(*PACKAGES)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "seeded 4 .deb files" in result.stdout
    download = runner.calls[1]
    assert download["cmd"] == "download"
    assert download["fetch"] == []
    assert runner.commands == ["update", "download", "install", "autoclean"]
    assert _debs(runner.cache) == sorted(PACKAGES)


def test_cache_miss_downloads_and_stages_the_archive_for_saving(tmp_path: Path) -> None:
    runner = Runner(tmp_path)

    result = runner.run(*PACKAGES)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "no cached .deb files" in result.stdout
    assert runner.calls[1]["fetch"] == PACKAGES
    # Obsolete archives are cleaned before the cache directory is refreshed.
    assert runner.commands == ["update", "download", "install", "autoclean"]
    assert _debs(runner.cache) == sorted(PACKAGES)
    assert runner.output.read_text(encoding="utf-8") == "cache-ready=true\n"


def test_failed_install_does_not_stage_the_cache(tmp_path: Path) -> None:
    runner = Runner(tmp_path)

    result = runner.run(*PACKAGES, APT_STUB_FAIL="update")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "autoclean" not in runner.commands
    assert not runner.cache.exists()
    assert runner.output.read_text(encoding="utf-8") == ""


def test_stalled_primary_mirror_falls_back_on_the_retry(tmp_path: Path) -> None:
    runner = Runner(tmp_path)
    (runner.config / "sources.list").write_text(DIRECT_LIST, encoding="utf-8")

    result = runner.run(*PACKAGES, APT_STUB_HANG_MIRROR=PRIMARY)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "attempt 1 failed or stalled (exit 124)" in result.stderr
    # The stalled primary is the only call on it; the repair runs first.
    assert runner.commands[-5:] == ["dpkg", "update", "download", "install", "autoclean"]
    assert runner.mirrors()[-2:] == [FALLBACK, FALLBACK]
    assert runner.calls[-5]["argv"] == ["--configure", "-a"]
    # The runner's mirror list and any directly named source move to the
    # fallback; unrelated sources are untouched.
    mirrors = (runner.config / "apt-mirrors.txt").read_text(encoding="utf-8")
    assert f"//{PRIMARY}/" not in mirrors
    assert mirrors.startswith(f"http://{FALLBACK}/ubuntu/\tpriority:1\n")
    assert (runner.config / "sources.list").read_text(encoding="utf-8") == DIRECT_LIST.replace(PRIMARY, FALLBACK)
    assert (runner.config / "sources.list.d" / "ubuntu.sources").read_text(encoding="utf-8") == UBUNTU_SOURCES
    assert (runner.config / "sources.list.d" / "microsoft-prod.list").read_text(encoding="utf-8") == MICROSOFT_LIST
    assert "succeeded on attempt 2" in result.stdout


def test_slow_download_is_not_cut_off_on_the_final_attempt(tmp_path: Path) -> None:
    runner = Runner(tmp_path)

    # Every download is slow: 8 s of steady progress against a 5 s cap.
    result = runner.run(*PACKAGES, APT_STUB_SLOW="download")

    assert result.returncode == 0, result.stdout + result.stderr
    # Attempt 1 hands the slow primary mirror over to the fallback ...
    assert "attempt 1 failed or stalled (exit 124)" in result.stderr
    # ... and the final attempt lets the slow but live download finish.
    assert "attempt 2 failed" not in result.stderr
    assert "succeeded on attempt 2" in result.stdout
    assert runner.commands == ["update", "download", "dpkg", "update", "download", "install", "autoclean"]
    assert runner.mirrors() == [PRIMARY, PRIMARY, FALLBACK, FALLBACK]


def test_killed_install_repairs_dpkg_before_the_retry(tmp_path: Path) -> None:
    # The dpkg phase hangs until `dpkg --configure -a` has run, as an
    # interrupted install would; the retry must repair before `apt-get update`.
    # The downloaded files are reused.
    runner = Runner(tmp_path)

    result = runner.run(*PACKAGES, APT_STUB_BEFORE_REPAIR="install:hang")

    assert result.returncode == 0, result.stdout + result.stderr
    assert runner.commands == [
        "update", "download", "install", "dpkg", "update", "download", "install", "autoclean",
    ]
    assert runner.calls[1]["fetch"] == PACKAGES
    assert runner.calls[5]["fetch"] == []
    assert "attempt 1 failed or stalled (exit 124)" in result.stderr


def test_dpkg_phase_stays_bounded_on_the_final_attempt(tmp_path: Path) -> None:
    runner = Runner(tmp_path)

    result = runner.run(*PACKAGES, APT_INSTALL_ATTEMPTS="1", APT_STUB_BEFORE_REPAIR="install:hang")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "attempt 1 failed or stalled (exit 124)" in result.stderr


def test_failed_dpkg_repair_is_reported_and_the_retry_still_runs(tmp_path: Path) -> None:
    runner = Runner(tmp_path)

    result = runner.run(*PACKAGES, dpkg_exit=1, APT_STUB_BEFORE_REPAIR="install:hang")

    # The repair failed, so the install still hangs; the retry itself ran.
    assert result.returncode == 1, result.stdout + result.stderr
    assert "warning: dpkg --configure -a did not complete before attempt 2" in result.stderr
    assert runner.commands == ["update", "download", "install", "dpkg", "update", "download", "install"]


def test_retry_without_a_primary_mirror_source_warns(tmp_path: Path) -> None:
    runner = Runner(tmp_path)
    (runner.config / "apt-mirrors.txt").write_text(f"https://{FALLBACK}/ubuntu/\tpriority:1\n", encoding="utf-8")

    result = runner.run(*PACKAGES, APT_STUB_BEFORE_REPAIR="update:fail")

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"warning: no apt source names {PRIMARY}" in result.stderr
    assert "succeeded on attempt 2" in result.stdout


def test_two_failed_attempts_fail_the_step(tmp_path: Path) -> None:
    runner = Runner(tmp_path)

    result = runner.run(*PACKAGES, APT_STUB_FAIL="download")

    assert result.returncode == 1, result.stdout + result.stderr
    assert runner.commands == ["update", "download", "dpkg", "update", "download"]
    assert "apt install failed after 2 attempts" in result.stderr


def test_missing_packages_is_a_usage_error(tmp_path: Path) -> None:
    runner = Runner(tmp_path)

    result = runner.run()

    assert result.returncode == 2
    assert runner.calls == []


def _workflow_steps() -> list[tuple[str, str, dict[str, Any], dict[str, Any]]]:
    steps = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        for job_name, job in (data.get("jobs") or {}).items():
            for step in job.get("steps") or []:
                steps.append((workflow.name, job_name, job, step))
    return steps


def _action_steps() -> dict[str, dict[str, Any]]:
    action = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
    assert action["runs"]["using"] == "composite"
    return {step.get("id", step["name"]): step for step in action["runs"]["steps"]}


def test_no_workflow_step_runs_apt_get_or_the_script_directly() -> None:
    direct = [
        f"{workflow}:{job}:{step.get('name', '?')}"
        for workflow, job, _, step in _workflow_steps()
        if "apt-get" in str(step.get("run", "")) or "ci_apt_install.sh" in str(step.get("run", ""))
    ]
    assert direct == [], f"install packages through {ACTION_REF} so the .deb cache applies: {direct}"


def test_install_steps_use_the_cached_action_without_a_step_timeout() -> None:
    install_steps = [
        (f"{workflow}:{job_name}", step)
        for workflow, job_name, _, step in _workflow_steps()
        if step.get("uses") == ACTION_REF
    ]
    assert len(install_steps) == 5, [where for where, _ in install_steps]
    for where, step in install_steps:
        assert step["with"]["packages"].split() == PACKAGES, where
        # A fixed step timeout cannot tell a slow mirror from a stuck one; a
        # 38-minute install on develop exited 0. Stalls are caught by apt.
        assert "timeout-minutes" not in step, f"{where}: install step must not set timeout-minutes"


def test_apt_action_restores_installs_then_saves_the_archive() -> None:
    steps = _action_steps()
    assert list(steps) == ["key", "restore", "install", "Save .deb archives"]
    restore, install, save = steps["restore"], steps["install"], steps["Save .deb archives"]
    uses = [step["uses"] for step in steps.values() if "uses" in step]
    assert uses == ["actions/cache/restore@v4", "actions/cache/save@v4"]
    cache_path = "${{ runner.temp }}/ci-apt-archives"
    assert restore["with"]["path"] == save["with"]["path"] == install["env"]["APT_ARCHIVE_CACHE_DIR"] == cache_path
    assert restore["with"]["key"] == save["with"]["key"] == "${{ steps.key.outputs.key }}"
    assert restore["with"]["restore-keys"] == "${{ steps.key.outputs.prefix }}"
    assert "scripts/ci_apt_install.sh" in install["run"]
    assert save["if"] == (
        "steps.restore.outputs.cache-hit != 'true' && steps.install.outputs.cache-ready == 'true'"
    )


def _cache_key(tmp_path: Path, packages: str, **env: str) -> dict[str, str]:
    bash = shutil.which("bash")
    if shutil.which("sha256sum") is None or bash is None:
        pytest.skip("sha256sum and bash are required to run the cache-key step")
    output = tmp_path / f"output-{len(list(tmp_path.iterdir()))}"
    result = subprocess.run(
        [bash, "-c", _action_steps()["key"]["run"]],
        env={"PATH": "/usr/bin:/bin:/sbin", "PACKAGES": packages, "GITHUB_OUTPUT": str(output), **env},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    pairs = (line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
    return {name: value for name, value in pairs}


def test_cache_key_follows_the_image_and_the_package_set(tmp_path: Path) -> None:
    image = {"ImageOS": "ubuntu24", "ImageVersion": "20261102.1"}
    key = _cache_key(tmp_path, " ".join(PACKAGES), **image)
    reordered = _cache_key(tmp_path, " ".join(reversed(PACKAGES)), **image)
    other_packages = _cache_key(tmp_path, "gdal-bin", **image)
    new_image = _cache_key(tmp_path, " ".join(PACKAGES), ImageOS="ubuntu24", ImageVersion="20261109.1")

    assert key["key"] == key["prefix"] + "20261102.1"
    assert key["prefix"].startswith("apt-debs-ubuntu24-")
    assert reordered == key
    assert other_packages["prefix"] != key["prefix"]
    # A new image misses the exact key but restores through the prefix.
    assert new_image["key"] != key["key"]
    assert new_image["prefix"] == key["prefix"]
