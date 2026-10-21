"""Exercise the battle-test runner without invoking the real test suite."""

import json
import shutil
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
