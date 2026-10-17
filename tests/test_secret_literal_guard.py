"""Subprocess regressions for the blocking credential-literal guard (#1578)."""

import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_secret_literals.py"
_SENTINEL = "credential-literal-sentinel-1578"


def run_guard(tmp_path, source):
    nested = tmp_path / "package"
    nested.mkdir()
    (nested / "example.py").write_text(source, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(_SCRIPT), str(tmp_path)],
        capture_output=True, text=True, timeout=30, check=False,
    )


def assert_rejected(result, line, value=_SENTINEL):
    assert result.returncode == 1
    output = result.stdout + result.stderr
    assert f"package/example.py:{line}:" in output
    assert value not in output
    assert "Traceback" not in output


@pytest.mark.parametrize("name", [
    "aws_secret_access_key", "aws_access_key_id", "aws_session_token",
    "password", "secret", "secret_key", "secretValue", "client_secret", "token", "api_key",
])
def test_literal_credential_keyword_fails(tmp_path, name):
    result = run_guard(tmp_path, f'boto3.client("s3", {name}="{_SENTINEL}")\n')
    assert_rejected(result, 1)


@pytest.mark.parametrize("name", [
    "password", "secret_key", "token", "api_key", "aws_access_key_id", "aws_session_token",
])
@pytest.mark.parametrize("constant", [False, True], ids=["literal", "module-constant"])
@pytest.mark.parametrize("shape", ["function", "argparse"])
def test_sensitive_defaults_fail(tmp_path, name, constant, shape):
    prefix = f'DEFAULT = "{_SENTINEL}"\n' if constant else ""
    value = "DEFAULT" if constant else repr(_SENTINEL)
    if shape == "function":
        source = f"def connect({name}={value}): pass\n"
    else:
        source = f"parser.add_argument('--{name.replace('_', '-')}', default={value})\n"
    assert_rejected(run_guard(tmp_path, prefix + source), 2 if constant else 1)


@pytest.mark.parametrize("source,line", [
    ('async def connect(*, password="VALUE"): pass\n', 1),
    ('def connect(password="VALUE", /): pass\n', 1),
    ('connect = lambda token="VALUE": None\n', 1),
    ('parser.add_argument("--credential", dest="password", default="VALUE")\n', 1),
    ('DEFAULT: str = "VALUE"\ndef connect(*, secret_key=DEFAULT): pass\n', 2),
    ('FIRST = DEFAULT = "VALUE"\nparser.add_argument("--token", default=DEFAULT)\n', 2),
    ('DEFAULT = "VALUE"\nconnect(password=DEFAULT)\n', 2),
    ('connect(\n    password="VALUE",\n)\n', 2),
])
def test_other_default_and_keyword_forms_fail(tmp_path, source, line):
    assert_rejected(run_guard(tmp_path, source.replace("VALUE", _SENTINEL)), line)


@pytest.mark.parametrize("prefix", ["AKIA", "ASIA"])
@pytest.mark.parametrize("shape", ["assignment", "unrelated-option", "docstring"])
def test_key_shaped_literals_fail_anywhere(tmp_path, prefix, shape):
    value = prefix + "A1" * 8
    if shape == "assignment":
        source = f'ordinary_name = "prefix:{value}:suffix"\n'
    elif shape == "unrelated-option":
        source = f'parser.add_argument("--output", default="{value}")\n'
    else:
        source = f'"""Example key: {value}"""\n'
    assert_rejected(run_guard(tmp_path, source), 1, value)


@pytest.mark.parametrize("source", [
    'connect(password="dummy")  # secret-guard: allow-dummy -- isolated test fixture\n',
    'def connect(secret_key="dummy"):  # secret-guard: allow-dummy -- isolated test fixture\n'
    '    pass\n',
    'parser.add_argument("--token", default="dummy")  # secret-guard: allow-dummy -- test fixture\n',
    '"""Use connect(password="<password>") and AWS_ACCESS_KEY_ID=<your-access-key>."""\n',
    '# Documentation placeholder: connect(secret_key="<secret>")\n',
    'parser.add_argument("--primary-key", default="id")\n',
    'parser.add_argument("--sort-key", default="name")\n',
    'def connect(primary_key="id", token_file="oauth.json"): pass\n',
    'def connect(password=None, *, token=None): pass\n',
    'connect(password=os.environ["PASSWORD"])\n',
    'parser.add_argument("--secret-key", default=None)\n',
])
def test_dummy_documentation_and_noncredential_defaults_pass(tmp_path, source):
    result = run_guard(tmp_path, source)
    assert result.returncode == 0, result.stdout + result.stderr


def test_explicit_dummy_key_fixture_passes(tmp_path):
    value = "AKIA" + "A1" * 8
    result = run_guard(
        tmp_path,
        f'KEY = "{value}"  # secret-guard: allow-dummy -- isolated scanner fixture\n',
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert value not in result.stdout + result.stderr


@pytest.mark.parametrize("prefix,suffix,line", [
    ('# secret-guard: allow-dummy -- another line\n', '', 2),
    ('', '  # secret-guard: allow-dummy', 1),
    ('marker = "# secret-guard: allow-dummy -- not a comment"\n', '', 2),
])
def test_dummy_exemption_is_local_and_requires_comment_reason(tmp_path, prefix, suffix, line):
    source = f'{prefix}connect(password="{_SENTINEL}"){suffix}\n'
    assert_rejected(run_guard(tmp_path, source), line)


def test_unparseable_source_fails_without_echoing_source(tmp_path):
    result = run_guard(tmp_path, f'connect(password="{_SENTINEL}"\n')
    assert_rejected(result, 1)
    assert "cannot parse Python source" in result.stdout


def test_empty_tree_fails_closed(tmp_path):
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), str(tmp_path)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 1
    assert "No Python sources found" in result.stdout


def test_unreadable_source_fails_without_echoing_bytes(tmp_path):
    (tmp_path / "example.py").write_bytes(b'password="\xff"\n')
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), str(tmp_path)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 1
    assert "example.py:1: cannot read Python source" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr


def test_ci_runs_guard_as_blocking_job():
    import yaml

    workflow = yaml.safe_load((_SCRIPT.parent.parent / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"]["secret-literal-guard"]
    assert not job.get("continue-on-error", False)
    assert "if" not in job
    steps = [step for step in job["steps"] if "check_secret_literals.py" in step.get("run", "")]
    assert len(steps) == 1
    assert steps[0]["run"].strip() == "python scripts/check_secret_literals.py"
    assert not steps[0].get("continue-on-error", False)
    assert "if" not in steps[0]
