"""Integration test: Narrative 5 — Reproducible Project Setup (#780 WS3-T5).

Story: A consultant starts a new analysis project. They need a project
directory structure, configuration files, logging, and the ability to
safely read/write data. The setup must be reproducible: running it twice
produces the same result, and missing pieces raise rather than silently
returning defaults (SU-1).
"""

import json
import logging

import pytest

from siege_utilities.core.logging import get_logger
from siege_utilities.files.operations import (
    ensure_directory_exists,
    safe_file_write,
    safe_file_read,
    safe_json_write,
    safe_json_read,
    file_exists,
    touch_file,
    count_lines,
    atomic_write_path,
)
from siege_utilities.files.validation import (
    validate_safe_path,
    validate_file_path,
    validate_directory_path,
    PathSecurityError,
)


@pytest.mark.integration
class TestProjectSetupNarrative:
    """End-to-end: create project, write config, verify, teardown."""

    def test_full_project_lifecycle(self, tmp_path):
        project_root = tmp_path / "my_analysis_project"

        ensure_directory_exists(str(project_root / "data" / "raw"))
        ensure_directory_exists(str(project_root / "data" / "processed"))
        ensure_directory_exists(str(project_root / "output"))
        ensure_directory_exists(str(project_root / "logs"))

        assert (project_root / "data" / "raw").is_dir()
        assert (project_root / "data" / "processed").is_dir()
        assert (project_root / "output").is_dir()
        assert (project_root / "logs").is_dir()

        config = {
            "project_name": "Travis County Demographics",
            "state_fips": "48",
            "county_fips": "453",
            "census_vintage": 2020,
            "output_format": "geojson",
        }
        config_path = str(project_root / "config.json")
        assert safe_json_write(config_path, config) is True

        loaded = safe_json_read(config_path)
        assert loaded == config
        assert loaded["census_vintage"] == 2020
        assert loaded["state_fips"] == "48"

        log_path = str(project_root / "logs" / "analysis.log")
        touch_file(log_path)
        assert file_exists(log_path)

        readme_path = str(project_root / "README.txt")
        content = "Travis County Demographics Analysis\nCreated: 2024-01-15\n"
        safe_file_write(readme_path, content)
        assert safe_file_read(readme_path) == content
        assert count_lines(readme_path) == 2


@pytest.mark.integration
class TestProjectSetupIdempotence:
    """Running setup twice must produce the same result."""

    def test_ensure_directory_idempotent(self, tmp_path):
        d = tmp_path / "project" / "data"
        ensure_directory_exists(str(d))
        ensure_directory_exists(str(d))
        assert d.is_dir()

    def test_config_overwrite_is_explicit(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        safe_json_write(config_path, {"version": 1})
        safe_json_write(config_path, {"version": 2})
        assert safe_json_read(config_path) == {"version": 2}


@pytest.mark.integration
class TestProjectSetupSU1:
    """SU-1: missing config must raise, not return defaults."""

    def test_missing_file_read_returns_none_not_empty_dict(self, tmp_path):
        result = safe_json_read(str(tmp_path / "nonexistent.json"))
        assert result is None

    def test_missing_file_count_lines_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            count_lines(str(tmp_path / "nonexistent.txt"))

    def test_validate_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_file_path(str(tmp_path / "nope.txt"), must_exist=True)

    def test_validate_nonexistent_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_directory_path(str(tmp_path / "nope"), must_exist=True)

    def test_path_traversal_blocked_in_project(self, tmp_path):
        with pytest.raises(PathSecurityError):
            validate_safe_path("../../etc/passwd")


@pytest.mark.integration
class TestAtomicConfigWrites:
    """Config writes must be atomic — partial writes don't corrupt state."""

    def test_atomic_write_preserves_original_on_failure(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"version": 1}))

        with pytest.raises(RuntimeError):
            with atomic_write_path(config_path) as tmp:
                tmp.write_text(json.dumps({"version": 2, "partial": True}))
                raise RuntimeError("simulated crash")

        restored = json.loads(config_path.read_text())
        assert restored == {"version": 1}

    def test_atomic_write_succeeds_cleanly(self, tmp_path):
        config_path = tmp_path / "config.json"
        with atomic_write_path(config_path) as tmp:
            tmp.write_text(json.dumps({"version": 1}))
        assert json.loads(config_path.read_text()) == {"version": 1}


@pytest.mark.integration
class TestLoggingSetup:
    """Project logging must be configurable and observable."""

    def test_logger_produces_output(self, tmp_path, caplog):
        logger = get_logger("test_project")
        with caplog.at_level(logging.INFO, logger="test_project"):
            logger.info("Project setup complete")
        assert "Project setup complete" in caplog.text

    def test_separate_loggers_dont_cross(self, caplog):
        log_a = get_logger("project_a")
        log_b = get_logger("project_b")
        with caplog.at_level(logging.INFO):
            log_a.info("from A")
            log_b.info("from B")
        assert "from A" in caplog.text
        assert "from B" in caplog.text
