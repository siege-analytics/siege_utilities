"""Property tests for file path utilities — SU-1 invariants.

Tests that path functions handle arbitrary input without crashing
and that sanitization is idempotent.
"""


import contextlib
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import example, given, settings
import hypothesis.strategies as st

from siege_utilities.files.validation import is_sensitive_path


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
    """Property tests for ensure_path_exists.

    ensure_path_exists really creates the directory and a .gitkeep, so feeding
    it arbitrary text on a live filesystem turns every generated string into a
    directory with a control-character or private-use name. That is how 24 of
    them reached the repo root (#1395) and how one crashed a Craft server that
    was watching a checkout (#1690). The properties are therefore split:
    arbitrary text never touches the filesystem, and the real-filesystem
    property only generates names a person could have typed.
    """

    @given(st.text(max_size=200))
    # A component over NAME_MAX (255 bytes) passes validation, and the OS then
    # refuses it on the real .gitkeep existence check, after mkdir was requested.
    @example("é" * 200)
    @settings(max_examples=50)
    def test_never_crashes_on_arbitrary_input(self, raw_path):
        """Arbitrary strings are rejected by validation, refused by the OS, or
        accepted with one mkdir request; the sandbox cwd stays empty."""
        from siege_utilities.files.paths import ensure_path_exists
        from siege_utilities.files.validation import PathSecurityError

        with tempfile.TemporaryDirectory() as sandbox, contextlib.chdir(sandbox), \
                mock.patch.object(Path, "mkdir", autospec=True) as mkdir, \
                mock.patch.object(Path, "touch", autospec=True) as touch:
            try:
                created = ensure_path_exists(raw_path)
            except (ValueError, TypeError, PathSecurityError):
                # PathSecurityError (e.g. embedded null byte) is a deliberate,
                # graceful rejection of a malicious path, not an unexpected crash.
                mkdir.assert_not_called()
            except OSError:
                # The OS refused the name (e.g. ENAMETOOLONG); this can happen
                # before or after the mkdir request, so only the cwd is checked.
                pass
            else:
                mkdir.assert_called_once_with(created, parents=True, exist_ok=True)
                # touch only runs when the .gitkeep is not already there.
                assert touch.call_count <= 1
                for call in touch.call_args_list:
                    assert call.args == (created / ".gitkeep",)
            assert os.listdir(sandbox) == [], f"{raw_path!r} wrote into the cwd"

    @given(
        st.from_regex(r"[A-Za-z0-9_-]{0,8}", fullmatch=True),
        st.sampled_from(
            [chr(c) for c in range(0x20)] + ["\x7f"] + [chr(c) for c in range(0x80, 0xA0)]
        ),
        st.from_regex(r"[A-Za-z0-9_-]{0,8}", fullmatch=True),
    )
    @settings(max_examples=100)
    def test_control_character_names_are_refused_without_writing(self, head, control, tail):
        """A new directory name containing a C0, DEL or C1 control character is
        rejected before anything is created (#1692)."""
        from siege_utilities.files.paths import ensure_path_exists
        from siege_utilities.files.validation import PathSecurityError

        name = head + control + tail
        with tempfile.TemporaryDirectory() as sandbox, contextlib.chdir(sandbox), \
                mock.patch.object(Path, "mkdir", autospec=True) as mkdir, \
                mock.patch.object(Path, "touch", autospec=True) as touch:
            with pytest.raises(PathSecurityError):
                ensure_path_exists(os.path.join("parent", name))
            mkdir.assert_not_called()
            touch.assert_not_called()
            assert os.listdir(sandbox) == [], f"{name!r} wrote into the cwd"

    @given(st.lists(
        st.from_regex(r"[A-Za-z0-9_-]{1,16}", fullmatch=True)
        # Ask the validator itself which names it blocks (private-key names
        # are an exact match on develop and a suffix match on main).
        .filter(lambda name: not is_sensitive_path(name)),
        min_size=1, max_size=4,
    ))
    @settings(max_examples=50)
    def test_creates_directory_and_gitkeep_inside_cwd(self, parts):
        """Well-formed relative paths are created, with a .gitkeep, under the
        current directory and nowhere else."""
        from siege_utilities.files.paths import ensure_path_exists

        with tempfile.TemporaryDirectory() as sandbox, contextlib.chdir(sandbox):
            created = ensure_path_exists(os.path.join(*parts))

            root = Path(sandbox).resolve()
            assert created == root.joinpath(*parts)
            assert created.is_dir()
            assert (created / ".gitkeep").is_file()
