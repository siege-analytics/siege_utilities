"""Root-import behavioral contracts for canonical setup helpers.

configure_shared_logging and create_default_profiles are canonical
(root-registered) public symbols the per-symbol coverage scanner (epic #1199)
reported as direct_coverage=False. Exercise them through the root
``siege_utilities`` namespace with real behavioral assertions.
"""

import logging

from siege_utilities import configure_shared_logging
from siege_utilities import create_default_profiles
from siege_utilities import log_warning


def test_configure_shared_logging_writes_records_to_file(tmp_path):
    log_file = tmp_path / "app.log"
    siege_logger = logging.getLogger("siege_utilities")
    root_logger = logging.getLogger()
    saved_siege = (list(siege_logger.handlers), siege_logger.level)
    saved_root = (list(root_logger.handlers), root_logger.level)
    try:
        result = configure_shared_logging(
            log_file_path=str(log_file), level="DEBUG"
        )
        # Documented return type is None; the effect is configuration.
        assert result is None
        log_warning("setup-contract-marker")
        for handler in siege_logger.handlers + root_logger.handlers:
            handler.flush()
        assert log_file.exists()
        assert "setup-contract-marker" in log_file.read_text(encoding="utf-8")
    finally:
        # Restore global logging state so this test does not leak handlers.
        for handler in list(siege_logger.handlers):
            if handler not in saved_siege[0]:
                handler.close()
        siege_logger.handlers = saved_siege[0]
        siege_logger.setLevel(saved_siege[1])
        for handler in list(root_logger.handlers):
            if handler not in saved_root[0]:
                handler.close()
        root_logger.handlers = saved_root[0]
        root_logger.setLevel(saved_root[1])


def test_create_default_profiles_returns_and_writes_profiles(tmp_path):
    user, clients = create_default_profiles(profile_location=tmp_path)

    assert type(user).__name__ == "UserProfile"
    assert isinstance(clients, list)
    assert clients  # at least one default client profile

    written = {p.name for p in tmp_path.rglob("*.yaml")}
    # The user profile plus one file per client profile are written to disk.
    assert "default.yaml" in written
    assert len(written) == 1 + len(clients)
