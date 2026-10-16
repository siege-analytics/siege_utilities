"""Property tests for file path utilities — SU-1 invariants.

Tests that path functions handle arbitrary input without crashing
and that sanitization is idempotent.
"""


import contextlib
import os
import tempfile
from pathlib import Path

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import assume, given, settings
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
        """ensure_path_exists should handle arbitrary strings gracefully.

        ensure_path_exists really creates each directory (plus a .gitkeep), so
        every example runs in its own temporary directory. Relative input used
        to land in the caller's cwd: random-named directories were committed to
        the repo root (#1395) and crashed a Craft server watching a checkout
        (#1690). Absolute input cannot be confined by a cwd change, so it is
        excluded; '..' traversal is already rejected by the validator.
        """
        from siege_utilities.files.paths import ensure_path_exists
        from siege_utilities.files.validation import PathSecurityError

        assume(not os.path.isabs(raw_path))

        with tempfile.TemporaryDirectory() as sandbox, contextlib.chdir(sandbox):
            try:
                created = ensure_path_exists(raw_path)
            except (OSError, ValueError, TypeError, PathSecurityError):
                # PathSecurityError (e.g. embedded null byte) is a deliberate,
                # graceful rejection of a malicious path, not an unexpected crash.
                return

            root = Path(sandbox).resolve()
            resolved = created.resolve()
            assert resolved == root or root in resolved.parents, (
                f"{raw_path!r} created {resolved}, outside the sandbox {root}"
            )
