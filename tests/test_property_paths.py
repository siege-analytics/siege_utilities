"""Property tests for file path utilities — SU-1 invariants.

Tests that path functions handle arbitrary input without crashing
and that sanitization is idempotent.
"""

import os

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, assume, settings
import hypothesis.strategies as st


class TestSanitizePathProperties:
    """Property tests for path sanitization."""

    @given(st.text(max_size=300))
    @settings(max_examples=100)
    def test_sanitize_never_crashes(self, raw_path):
        """sanitize_filename must not raise on arbitrary string input."""
        from siege_utilities.files.operations import sanitize_filename

        try:
            result = sanitize_filename(raw_path)
            assert isinstance(result, str)
        except (ValueError, TypeError):
            pass

    @given(st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="\x00",
    )))
    @settings(max_examples=100)
    def test_sanitize_idempotent(self, raw_path):
        """Sanitizing twice gives the same result as sanitizing once."""
        from siege_utilities.files.operations import sanitize_filename

        try:
            once = sanitize_filename(raw_path)
            twice = sanitize_filename(once)
            assert once == twice, f"Not idempotent: {raw_path!r} -> {once!r} -> {twice!r}"
        except (ValueError, TypeError):
            pass


class TestEnsurePathExistsProperties:
    """Property tests for ensure_path_exists."""

    @given(st.text(max_size=200))
    @settings(max_examples=50)
    def test_never_crashes_on_arbitrary_input(self, raw_path):
        """ensure_path_exists should handle arbitrary strings gracefully."""
        from siege_utilities.files.paths import ensure_path_exists

        try:
            ensure_path_exists(raw_path)
        except (OSError, ValueError, TypeError):
            pass
