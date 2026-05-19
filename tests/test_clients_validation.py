"""Tests for siege_utilities.config.clients — client_code validation.

PR #443 B12 follow-up per CR feedback: client_code validation must
apply on the load path too, not just save.
"""

from __future__ import annotations

import pytest


class TestValidateClientCode:
    def test_accepts_normal_codes(self):
        from siege_utilities.config.clients import _validate_client_code
        for code in ["ACME", "acme_001", "test-client", "X1", "A" * 64]:
            assert _validate_client_code(code) == code

    @pytest.mark.parametrize("bad", [
        "",
        "../etc/passwd",
        "client/with/slash",
        "client\\with\\backslash",
        "client with space",
        "code.with.dots",
        "A" * 65,  # too long
    ])
    def test_rejects_unsafe(self, bad):
        from siege_utilities.config.clients import _validate_client_code
        with pytest.raises(ValueError, match="client_code"):
            _validate_client_code(bad)

    def test_rejects_non_string(self):
        from siege_utilities.config.clients import _validate_client_code
        with pytest.raises(ValueError):
            _validate_client_code(123)  # type: ignore[arg-type]


class TestLoadClientProfile:
    """load_client_profile must validate client_code before building a path."""

    def test_rejects_traversal(self, tmp_path):
        from siege_utilities.config.clients import load_client_profile
        with pytest.raises(ValueError, match="client_code"):
            load_client_profile("../foo", str(tmp_path))

    def test_loads_valid_profile(self, tmp_path):
        from siege_utilities.config.clients import (
            load_client_profile, save_client_profile,
        )
        # Build a minimal profile and round-trip it.
        profile = {
            "client_id": "uuid-1",
            "client_name": "Acme",
            "client_code": "ACME",
            "contact_info": {"primary_contact": "x", "email": "x@y.z"},
            "metadata": {},
            "design_artifacts": {},
            "preferences": {},
        }
        save_client_profile(profile, str(tmp_path))
        out = load_client_profile("ACME", str(tmp_path))
        assert out is not None
        assert out["client_code"] == "ACME"
