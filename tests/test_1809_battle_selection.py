"""R-1809 battle-lane selection and artifact guards (#1809 / #1475).

The overnight battle wrapper must not run a broad ``pytest tests/``: its runner
has no Postgres service and must not execute the heavy notebook suite. Both of
its pytest invocations (the uv branch and the python branch) must carry the
same exclusions as the main CI lane: marker ``not integration and not postgis``
and ``--ignore=tests/test_notebooks.py``.

These checks are behavioural. Each branch of the real shell script runs with a
stub ``pytest`` on ``PATH`` that records the argv it receives, and the guard
parses pytest's effective options from that argv (the last ``-m`` wins;
``--ignore`` may be ``=VALUE`` or a separate token). Comments, quoting and line
layout therefore cannot fool it. The reviewer's four unsafe variants must be
rejected and its four safe reformats accepted, on both branches.

A failed ``tee`` write must fail the run: no exit 0 and no summary
``exit_code`` 0 without an output artifact.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

WRAPPER = Path(__file__).resolve().parents[1] / "scripts" / "run_overnight_comprehensive.sh"
REQUIRED_MARKER = "not integration and not postgis"
REQUIRED_IGNORE = "tests/test_notebooks.py"
# pytest options whose next token is a value, so it is never read as -m/--ignore.
VALUE_OPTIONS = {"-o", "-p", "-k", "-c", "--rootdir", "--override-ini", "--confcutdir"}

MARKER_LINE = '        -m "not integration and not postgis" \\\n'
IGNORE_LINE = "        --ignore=tests/test_notebooks.py \\\n"
TEE_LINE = "2>&1 | tee overnight_results/test_output.txt\n"
PYTEST_TARGET = "pytest tests/ \\\n"


def effective_selection(args):
    """Return pytest's effective (marker, ignores) for an argv list."""
    marker = None
    ignores = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in VALUE_OPTIONS:
            i += 2
            continue
        if arg == "-m" and i + 1 < len(args):
            marker = args[i + 1]
            i += 2
            continue
        if arg.startswith("-m") and not arg.startswith("--") and len(arg) > 2:
            marker = arg[2:]
        elif arg == "--ignore" and i + 1 < len(args):
            ignores.append(args[i + 1])
            i += 2
            continue
        elif arg.startswith("--ignore="):
            ignores.append(arg.split("=", 1)[1])
        i += 1
    return marker, ignores


def selection_is_safe(args):
    marker, ignores = effective_selection(args)
    return marker == REQUIRED_MARKER and REQUIRED_IGNORE in {os.path.normpath(p) for p in ignores}


def _write_executable(path, source):
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def run_wrapper(tmp_path, script_text, runner, *, pytest_exit=0, block_output=False):
    """Run the wrapper text in a disposable repo with stub tools; return run facts."""
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    (repo / "tests").mkdir()
    script = scripts / WRAPPER.name
    script.write_text(script_text, encoding="utf-8")
    if block_output:
        # A directory where the log file belongs makes the tee write fail.
        (repo / "overnight_results" / "test_output.txt").mkdir(parents=True)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("dirname", "mkdir", "date", "tee", "cat"):
        executable = shutil.which(tool)
        assert executable is not None, f"Required shell utility missing: {tool}"
        (bin_dir / tool).symlink_to(executable)

    argv_log = tmp_path / "pytest-argv.jsonl"
    _write_executable(
        bin_dir / "pytest",
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "with open(os.environ['PYTEST_ARGV_LOG'], 'a', encoding='utf-8') as log:\n"
        "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "print('pytest stub output')\n"
        "sys.exit(int(os.environ['PYTEST_EXIT_CODE']))\n",
    )
    _write_executable(
        bin_dir / "python",
        "#!/bin/bash\n"
        'if [[ "$1" == "--version" ]]; then echo "Python test stub"; exit 0; fi\n'
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
        cwd=tmp_path,
        env={
            "PATH": str(bin_dir),
            "PYTEST_ARGV_LOG": str(argv_log),
            "PYTEST_EXIT_CODE": str(pytest_exit),
        },
        capture_output=True,
        text=True,
        timeout=15,
    )
    invocations = []
    if argv_log.exists():
        invocations = [json.loads(line) for line in argv_log.read_text(encoding="utf-8").splitlines()]
    return result, invocations, repo / "overnight_results"


def _replace_both(text, old, new):
    assert text.count(old) == 2, f"expected one occurrence per branch of {old!r}"
    return text.replace(old, new)


def _append_comment(text, comment):
    return _replace_both(text, TEE_LINE, TEE_LINE.rstrip("\n") + f"  # {comment}\n")


# The reviewer's variants (#1475 review of 85b49cb3): four that the old substring
# guard accepted although pytest's effective selection is unsafe, and four safe
# reformats that it rejected.
UNSAFE_VARIANTS = {
    "marker-only-in-comment": lambda t: _append_comment(
        _replace_both(t, MARKER_LINE, ""), '-m "not integration and not postgis"'),
    "later-weaker-marker": lambda t: _replace_both(
        t, MARKER_LINE, MARKER_LINE + '        -m "not integration" \\\n'),
    "marker-inside-junit-option": lambda t: _replace_both(
        t, MARKER_LINE, "        -o 'junit_suite_name=-m \"not integration and not postgis\"' \\\n"),
    "ignore-only-in-comment": lambda t: _append_comment(
        _replace_both(t, IGNORE_LINE, ""), "--ignore=tests/test_notebooks.py"),
}
SAFE_VARIANTS = {
    "single-quoted-marker": lambda t: _replace_both(
        t, MARKER_LINE, "        -m 'not integration and not postgis' \\\n"),
    "separate-ignore-value": lambda t: _replace_both(
        t, IGNORE_LINE, "        --ignore tests/test_notebooks.py \\\n"),
    "extra-whitespace-before-target": lambda t: _replace_both(
        t, PYTEST_TARGET, "pytest     tests/ \\\n"),
    "continuation-before-target": lambda t: _replace_both(
        t, PYTEST_TARGET, "pytest \\\n        tests/ \\\n"),
}


@pytest.mark.parametrize("runner", ["uv", "python"])
def test_real_wrapper_passes_main_lane_selection(tmp_path, runner):
    result, invocations, _ = run_wrapper(tmp_path, WRAPPER.read_text(encoding="utf-8"), runner)

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(invocations) == 1
    assert invocations[0][0] == "tests/"
    assert effective_selection(invocations[0]) == (REQUIRED_MARKER, [REQUIRED_IGNORE])


@pytest.mark.parametrize("runner", ["uv", "python"])
@pytest.mark.parametrize("variant", sorted(UNSAFE_VARIANTS))
def test_guard_rejects_unsafe_variants(tmp_path, runner, variant):
    text = UNSAFE_VARIANTS[variant](WRAPPER.read_text(encoding="utf-8"))

    result, invocations, _ = run_wrapper(tmp_path, text, runner)

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(invocations) == 1
    assert not selection_is_safe(invocations[0]), invocations[0]


@pytest.mark.parametrize("runner", ["uv", "python"])
@pytest.mark.parametrize("variant", sorted(SAFE_VARIANTS))
def test_guard_accepts_safe_reformats(tmp_path, runner, variant):
    text = SAFE_VARIANTS[variant](WRAPPER.read_text(encoding="utf-8"))

    result, invocations, _ = run_wrapper(tmp_path, text, runner)

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(invocations) == 1
    assert selection_is_safe(invocations[0]), invocations[0]


@pytest.mark.parametrize("runner", ["uv", "python"])
@pytest.mark.parametrize("pytest_exit, expected_exit", [(0, 1), (3, 3)])
def test_failed_tee_write_fails_the_run(tmp_path, runner, pytest_exit, expected_exit):
    result, invocations, results_dir = run_wrapper(
        tmp_path, WRAPPER.read_text(encoding="utf-8"), runner,
        pytest_exit=pytest_exit, block_output=True,
    )

    assert len(invocations) == 1
    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert "could not write overnight_results/test_output.txt" in result.stderr
    assert not (results_dir / "test_output.txt").is_file()
    summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["exit_code"] == expected_exit
    assert summary["pytest_exit_code"] == pytest_exit
    assert summary["tee_exit_code"] != 0
    assert summary["output_artifact"] == "absent"


@pytest.mark.parametrize("runner", ["uv", "python"])
def test_successful_run_writes_a_real_artifact(tmp_path, runner):
    result, _, results_dir = run_wrapper(tmp_path, WRAPPER.read_text(encoding="utf-8"), runner)

    assert result.returncode == 0, result.stdout + result.stderr
    artifact = results_dir / "test_output.txt"
    assert artifact.is_file()
    assert "pytest stub output" in artifact.read_text(encoding="utf-8")
    summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["exit_code"] == 0
    assert summary["tee_exit_code"] == 0
    assert summary["output_artifact"] == "written"
