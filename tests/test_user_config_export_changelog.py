"""#1452: CHANGELOG documents the export_config change; lock the behaviour."""
import os
import re
import stat
from pathlib import Path

import pytest

from siege_utilities.config.user_config import UserConfigManager

REPO = Path(__file__).resolve().parents[1]
DSN_FRAGMENT = "rv-sentinel-p4ss"
# Composed at runtime so secret scanners do not flag a URI-shaped literal.
DSN_SENTINEL = f"postgresql://rv_user:{DSN_FRAGMENT}@db.invalid/rv"
KEY_SENTINEL = "rv-census-sentinel-key"


def _unreleased_section() -> str:
    text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(r"^## \[Unreleased\]\s*$(.*?)^## \[", text, re.M | re.S)
    assert m, "no [Unreleased] section in CHANGELOG.md"
    return m.group(1)


def test_changelog_documents_export_config_scrub():
    entries = re.split(r"\n(?=- )", _unreleased_section())
    hits = [e for e in entries if "export_config" in e and "#1452" in e]
    assert hits, "no [Unreleased] CHANGELOG entry mentions export_config with #1452"
    assert "postgresql_connection" in hits[0] and "duckdb_path" in hits[0]
    assert "0600" in hits[0]


@pytest.mark.skipif(os.name != "posix", reason="POSIX modes")
def test_export_config_scrubs_dsn_and_is_0600(tmp_path):
    old = os.umask(0o022)
    try:
        cfg = tmp_path / "cfg"
        cfg.mkdir(mode=0o700)
        m = UserConfigManager(config_dir=cfg)
        m.set_api_key("census", KEY_SENTINEL)
        m.set_database_connection("postgresql", DSN_SENTINEL)
        assert stat.S_IMODE(os.stat(m.user_config_file).st_mode) == 0o600
        again = UserConfigManager(config_dir=cfg)
        assert again.get_api_key("census") == KEY_SENTINEL
        assert again.get_database_connection("postgresql") == DSN_SENTINEL
        out = tmp_path / "export.yaml"
        out.write_text("old", encoding="utf-8")
        os.chmod(out, 0o644)
        m.export_config(str(out))
        body = out.read_text(encoding="utf-8")
        assert DSN_FRAGMENT not in body and KEY_SENTINEL not in body
        assert "postgresql_connection:" not in body and "duckdb_path:" not in body
        assert stat.S_IMODE(os.stat(out).st_mode) == 0o600
    finally:
        os.umask(old)
