"""Release process guards (#1419).

PyPI releases go only through .github/workflows/publish-tag.yml: v* tag,
tag == pyproject version, tagged commit on main, full CI on the tag, then
trusted publishing with attestations. Nothing else in the repository may
upload to PyPI.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from scripts import release_manager

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow(name: str) -> dict:
    data = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    # PyYAML (YAML 1.1) reads the bare key `on` as boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return data


PUBLISH = _workflow("publish-tag.yml")
CI = _workflow("ci.yml")


def test_publish_triggers_only_on_v_tags():
    assert PUBLISH["on"]["push"] == {"tags": ["v*"]}
    assert set(PUBLISH["on"]) <= {"push", "workflow_dispatch"}
    assert PUBLISH["on"].get("workflow_dispatch") in (None, {})


def test_publish_job_waits_for_tag_check_full_ci_and_build():
    jobs = PUBLISH["jobs"]
    assert jobs["ci"]["uses"] == "./.github/workflows/ci.yml"
    assert jobs["ci"]["needs"] == "verify-tag"
    assert {"verify-tag", "ci"} <= set(jobs["build"]["needs"])
    assert {"verify-tag", "ci", "build"} <= set(jobs["publish"]["needs"])


def test_verify_tag_checks_ref_version_and_main():
    script = "\n".join(step.get("run", "") for step in PUBLISH["jobs"]["verify-tag"]["steps"])
    assert "refs/tags/v*" in script
    assert '"${TAG}" != "v${PKG_VERSION}"' in script
    assert "tomllib" in script and "['project']['version']" in script
    assert 'merge-base --is-ancestor "${GITHUB_SHA}" origin/main' in script


def test_publish_uses_the_pypa_action_with_the_repository_token():
    # The existing PYPI_API_TOKEN secret authenticates until a trusted
    # publisher is configured; attestations stay requested so dropping the
    # `password:` line is the only change needed to switch (RELEASING.md).
    job = PUBLISH["jobs"]["publish"]
    assert job["permissions"]["id-token"] == "write"
    assert job["environment"]["name"] == "pypi"
    publish_steps = [s for s in job["steps"] if "pypa/gh-action-pypi-publish" in s.get("uses", "")]
    assert len(publish_steps) == 1
    assert publish_steps[0]["with"]["attestations"] is True
    assert publish_steps[0]["with"]["password"] == "${{ secrets.PYPI_API_TOKEN }}"
    assert PUBLISH["permissions"] == {"contents": "read"}


def test_publish_build_runs_wheel_contents_check():
    runs = [s.get("run", "") for s in PUBLISH["jobs"]["build"]["steps"]]
    assert any("scripts/check_wheel_contents.py dist/*.whl" in r for r in runs)


def test_ci_is_callable_and_never_publishes():
    assert "workflow_call" in CI["on"]
    assert "release" not in CI["on"]
    assert "release" not in CI["jobs"]


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.y*ml")), ids=lambda p: p.name)
def test_no_workflow_runs_twine_or_reads_the_token_outside_publish(path):
    text = path.read_text(encoding="utf-8")
    assert "twine upload" not in text
    if path.name != "publish-tag.yml":
        assert "PYPI_API_TOKEN" not in text


def test_pypi_token_is_used_only_by_the_publish_action():
    wf = yaml.safe_load((WORKFLOWS / "publish-tag.yml").read_text(encoding="utf-8"))
    users = []
    for job_name, job in wf["jobs"].items():
        for step in job.get("steps", []):
            if "PYPI_API_TOKEN" in yaml.safe_dump(step):
                users.append((job_name, step.get("uses"), step.get("with", {}).get("password")))
    assert users == [("publish", "pypa/gh-action-pypi-publish@release/v1",
                      "${{ secrets.PYPI_API_TOKEN }}")]
    assert wf["jobs"]["publish"]["needs"] == ["verify-tag", "ci", "build"]


def test_upload_to_production_pypi_is_refused(monkeypatch, tmp_path):
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "example.whl").write_bytes(b"fixture")
    monkeypatch.setattr(release_manager, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("PYPI_API_TOKEN", "sentinel-1419-not-a-token")
    run = Mock(spec=subprocess.run)
    monkeypatch.setattr(release_manager.subprocess, "run", run)
    logger = Mock()
    monkeypatch.setattr(release_manager, "logger", logger)

    assert release_manager.upload_to_pypi(repository="pypi") is False

    run.assert_not_called()
    assert "Manual PyPI uploads are prohibited" in logger.error.call_args.args[0]


def test_release_flow_does_not_upload_or_need_a_token(monkeypatch):
    monkeypatch.delenv("PYPI_API_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "release_manager.py", "--release", "--bump-type", "patch",
        "--release-notes", "notes", "--skip-tests", "--skip-github", "--dry-run",
    ])
    tagged = []
    monkeypatch.setattr(release_manager, "check_ci_status", lambda: True)
    monkeypatch.setattr(release_manager, "clean_build_artifacts", lambda: True)
    monkeypatch.setattr(release_manager, "_current_branch", lambda: "develop")
    monkeypatch.setattr(release_manager, "commit_release_metadata", lambda v, d: True)
    monkeypatch.setattr(release_manager, "merge_develop_to_main", lambda d: True)
    monkeypatch.setattr(
        release_manager, "git_tag_and_push",
        lambda v, notes, d: tagged.append(v) or True,
    )
    upload = Mock(side_effect=AssertionError("release must not upload"))
    monkeypatch.setattr(release_manager, "upload_to_pypi", upload)

    release_manager.main()

    upload.assert_not_called()
    assert len(tagged) == 1


def test_release_flow_stops_when_tagging_fails(monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "release_manager.py", "--release", "--bump-type", "patch",
        "--release-notes", "notes", "--skip-tests", "--skip-github", "--dry-run",
    ])
    monkeypatch.setattr(release_manager, "check_ci_status", lambda: True)
    monkeypatch.setattr(release_manager, "clean_build_artifacts", lambda: True)
    monkeypatch.setattr(release_manager, "_current_branch", lambda: "develop")
    monkeypatch.setattr(release_manager, "commit_release_metadata", lambda v, d: True)
    monkeypatch.setattr(release_manager, "merge_develop_to_main", lambda d: True)
    monkeypatch.setattr(release_manager, "git_tag_and_push", lambda v, notes, d: False)
    # Before #1419 a tagging failure was non-fatal and the upload ran anyway.
    monkeypatch.setattr(release_manager, "upload_to_pypi", lambda *a, **kw: True)

    with pytest.raises(SystemExit) as exc:
        release_manager.main()
    assert exc.value.code == 1


def test_tag_push_sends_only_the_new_tag(monkeypatch):
    calls = []
    monkeypatch.setattr(release_manager, "_current_branch", lambda: "main")
    monkeypatch.setattr(release_manager, "_git", lambda args, **kw: calls.append(args))

    assert release_manager.git_tag_and_push("9.9.9", "notes") is True

    assert ["push", "origin", "refs/tags/v9.9.9"] in calls
    assert not any("--tags" in args for args in calls)


def test_etter_extra_caps_pandas_below_3():
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"]["optional-dependencies"]
    assert "pandas>=2.0.0,<3.0" in extras["etter"]


def test_extras_comments_do_not_claim_removal_in_3_19():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert not re.search(r"extra removed in v?3\.19", text)


@pytest.mark.parametrize(
    "version", ["3.18.0", "3.19.0", "3.20.0", "3.21.0", "3.22.0", "3.22.1", "3.23.0"]
)
def test_changelog_has_an_entry_for_each_3_18_to_3_23_tag(version):
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", text, re.M)


def test_changelog_says_3_21_0_was_not_published():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    section = text.split("## [3.21.0]", 1)[1].split("\n## [", 1)[0]
    assert "Not published to PyPI" in section
