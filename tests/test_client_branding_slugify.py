"""Tests for _slugify_client_name in siege_utilities.reporting.client_branding.

PR follow-up: client_name was previously normalised only by lowercasing
and replacing spaces, leaving `../` and OS path separators free to
escape the branding directory.
"""

from __future__ import annotations

import pytest


class TestSlugifyClientName:

    @pytest.mark.parametrize("raw,expected", [
        ("Acme", "acme"),
        ("Acme Corp", "acme_corp"),
        ("Acme  Corp", "acme_corp"),                # double space
        ("ACME-CORP", "acme_corp"),                 # dash → _
        ("Acme/Corp", "acme_corp"),                 # slash → _
        ("Acme.Corp", "acme_corp"),                 # dot → _
        ("../etc", "etc"),                          # traversal → _
        ("client@email.com", "client_email_com"),
    ])
    def test_safe_normalization(self, raw, expected):
        from siege_utilities.reporting.client_branding import _slugify_client_name
        assert _slugify_client_name(raw) == expected

    @pytest.mark.parametrize("bad", ["", "   ", "...", "///", None])
    def test_unusable_inputs_raise(self, bad):
        from siege_utilities.reporting.client_branding import _slugify_client_name
        with pytest.raises((ValueError, TypeError)):
            _slugify_client_name(bad)  # type: ignore[arg-type]

    def test_path_traversal_cannot_escape_dir(self, tmp_path):
        """The slug never contains path separators, so building
        config_dir / slug is always confined to config_dir."""
        from siege_utilities.reporting.client_branding import _slugify_client_name
        slug = _slugify_client_name("../../../etc/passwd")
        full = (tmp_path / slug).resolve()
        assert full.is_relative_to(tmp_path.resolve())
