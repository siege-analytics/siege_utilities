"""Exercise the battle-test runner in disposable repository layouts."""

import json
import shutil
import shlex
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_overnight_comprehensive.sh"


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


@pytest.mark.parametrize("runner", ["uv", "python"])
@pytest.mark.parametrize("exit_code", [1, 0, 4, 5])
def test_overnight_runs_repo_tests_and_preserves_status(
    tmp_path: Path, runner: str, exit_code: int
) -> None:
    # Copy only the script into a disposable repository layout. Reports must
    # stay there even when the caller starts outside the repository.
    repo = tmp_path / "repo with spaces"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    (repo / "tests").mkdir()
    script = scripts / SCRIPT.name
    shutil.copyfile(SCRIPT, script)
    caller = tmp_path / "caller"
    caller.mkdir()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # Use an allowlisted PATH so neither a real uv nor a real pytest can run.
    for tool in ("dirname", "mkdir", "date", "tee", "cat"):
        executable = shutil.which(tool)
        assert executable is not None, f"Required shell utility missing: {tool}"
        (bin_dir / tool).symlink_to(executable)

    invocation_file = tmp_path / "pytest-invocation.json"
    _write_executable(
        bin_dir / "pytest",
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['PYTEST_INVOCATION']).write_text(json.dumps({\n"
        "    'cwd': os.getcwd(), 'args': sys.argv[1:]\n"
        "}), encoding='utf-8')\n"
        "print('pytest stub stdout')\n"
        "print('pytest stub stderr', file=sys.stderr)\n"
        "sys.exit(int(os.environ['PYTEST_EXIT_CODE']))\n",
    )
    _write_executable(
        bin_dir / "python",
        "#!/bin/bash\n"
        'if [[ "$1" == "--version" ]]; then\n'
        "    echo 'Python test stub'\n"
        "    exit 0\n"
        "fi\n"
        '[[ "$1" == "-m" && "$2" == "pytest" ]] || exit 97\n'
        "shift 2\n"
        'exec pytest "$@"\n',
    )
    if runner == "uv":
        _write_executable(
            bin_dir / "uv",
            "#!/bin/bash\n"
            '[[ "$1" == "run" && "$2" == "pytest" ]] || exit 97\n'
            "shift\n"
            'exec "$@"\n',
        )

    result = subprocess.run(
        ["/bin/bash", str(script)],
        cwd=caller,
        env={
            "PATH": str(bin_dir),
            "PYTEST_INVOCATION": str(invocation_file),
            "PYTEST_EXIT_CODE": str(exit_code),
        },
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == exit_code, result.stdout + result.stderr
    invocation = json.loads(invocation_file.read_text(encoding="utf-8"))
    target = (Path(invocation["cwd"]) / invocation["args"][0]).resolve()
    assert target == (repo / "tests").resolve()
    assert target.is_dir()

    results_dir = repo / "overnight_results"
    summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["exit_code"] == exit_code
    assert Path(summary["script_dir"]) == scripts.resolve()
    output = (results_dir / "test_output.txt").read_text(encoding="utf-8")
    assert "pytest stub stdout" in output
    assert "pytest stub stderr" in output
    for report in (
        "html:overnight_results/coverage_html",
        "json:overnight_results/coverage.json",
    ):
        assert f"--cov-report={report}" in invocation["args"]
        report_path = Path(invocation["cwd"]) / report.split(":", 1)[1]
        assert report_path.parent.resolve() == results_dir.resolve()
    assert not (scripts / "overnight_results").exists()
    assert not (caller / "overnight_results").exists()


@pytest.mark.parametrize("passes", [False, True], ids=["assertion-fails", "passes"])
def test_overnight_preserves_real_pytest_result(tmp_path: Path, passes: bool) -> None:
    repo = tmp_path / "real pytest repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / SCRIPT.name
    shutil.copyfile(SCRIPT, script)
    tests = repo / "tests"
    tests.mkdir()
    package = repo / "siege_utilities"
    package.mkdir()
    (package / "__init__.py").write_text("ANSWER = 42\n", encoding="utf-8")
    (tests / "test_real_canary.py").write_text(
        "from siege_utilities import ANSWER\n\n"
        "def test_real_assertion():\n"
        f"    assert ANSWER == {42 if passes else 43}\n",
        encoding="utf-8",
    )
    caller = tmp_path / "outside caller"
    caller.mkdir()
    bin_dir = tmp_path / "real-bin"
    bin_dir.mkdir()
    for tool in ("dirname", "mkdir", "date", "tee", "cat"):
        executable = shutil.which(tool)
        assert executable is not None, f"Required shell utility missing: {tool}"
        (bin_dir / tool).symlink_to(executable)
    # Select the wrapper's python branch without exposing host uv. This is the
    # actual test interpreter and pytest, not a command/status stub. Load only
    # the required coverage plugin so unrelated host plugins cannot interfere.
    _write_executable(
        bin_dir / "python",
        "#!/bin/bash\n" + f'exec {shlex.quote(sys.executable)} "$@"\n',
    )
    result = subprocess.run(
        ["/bin/bash", str(script)],
        cwd=caller,
        env={
            "PATH": str(bin_dir),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTEST_ADDOPTS": "-p pytest_cov",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    expected = 0 if passes else 1
    assert result.returncode == expected, result.stdout + result.stderr
    reports = repo / "overnight_results"
    output = (reports / "test_output.txt").read_text(encoding="utf-8")
    assert "test_real_canary.py::test_real_assertion" in output
    assert ("1 passed" if passes else "1 failed") in output
    if not passes:
        assert "assert 42 == 43" in output
    assert "ERROR collecting" not in output
    summary = json.loads((reports / "summary.json").read_text(encoding="utf-8"))
    assert summary["exit_code"] == summary["pytest_exit_code"] == expected
    assert summary["tee_exit_code"] == 0
    assert summary["output_artifact"] == "written"
    assert (reports / "coverage.json").is_file()
    assert (reports / "coverage_html" / "index.html").is_file()
    assert not (scripts / "overnight_results").exists()
    assert not (caller / "overnight_results").exists()
