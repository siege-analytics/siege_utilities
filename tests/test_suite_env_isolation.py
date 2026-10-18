"""A test run never reads or writes the developer's real config (#1717).

The outer test runs pytest in a subprocess with SIEGE_USER_CONFIG_DIR and
SIEGE_SETTINGS_FILE pointing at sentinels, and checks they are unchanged. The
inner test only runs inside that subprocess: it checks conftest dropped the
variables and then saves a user profile, which on develop @ 1dd8c32d rewrote
the sentinel directory.
"""

import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

_PROBE = "SIEGE_TEST_ENV_ISOLATION_PROBE"


@pytest.mark.skipif(os.environ.get(_PROBE) != "1", reason="runs inside the subprocess only")
def test_inner_inherited_siege_variables_are_dropped():
    assert "SIEGE_USER_CONFIG_DIR" not in os.environ
    assert "SIEGE_SETTINGS_FILE" not in os.environ
    assert "SIEGE_DEFAULT_PROBE_SETTING" not in os.environ
    assert os.environ[_PROBE] == "1"  # test-run controls pass through

    from siege_utilities.config.user_config import UserConfigManager

    UserConfigManager().update_user_profile(username="isolation-probe")


def _fingerprint(path: Path):
    st = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return digest, stat.S_IMODE(st.st_mode)


def test_suite_leaves_exported_config_untouched(tmp_path):
    config_dir = tmp_path / "real_config"
    config_dir.mkdir()
    os.chmod(config_dir, 0o2700)
    user_config = config_dir / "user_config.yaml"
    user_config.write_text("username: sentinel\n")
    settings_file = tmp_path / "siege_settings.yaml"
    settings_file.write_text("sentinel: true\n")
    watched = [config_dir, user_config, settings_file]
    before = [_fingerprint(p) for p in watched]

    env = dict(os.environ)
    env.update({
        "SIEGE_USER_CONFIG_DIR": str(config_dir),
        "SIEGE_SETTINGS_FILE": str(settings_file),
        "SIEGE_DEFAULT_PROBE_SETTING": "inherited",
        _PROBE: "1",
    })
    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:randomly",
         "-o", "addopts=", f"{Path(__file__).resolve()}::test_inner_inherited_siege_variables_are_dropped"],
        cwd=repo, env=env, capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    assert "1 passed" in result.stdout, result.stdout[-3000:]
    assert [_fingerprint(p) for p in watched] == before
    assert sorted(os.listdir(config_dir)) == ["user_config.yaml"]
