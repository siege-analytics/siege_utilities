"""Shared internal helpers for the git sub-package."""

import subprocess

from siege_utilities.exceptions import GitError


def run_git_command(*args, repo_path: str = ".", check: bool = True) -> str:
    """Run a git command and return stdout.

    When ``check=True`` (default), raises ``GitError`` on non-zero exit.
    When ``check=False``, returns ``""`` on failure.

    .. note::
        # SU-1: intentional — check=False callers (upstream detection,
        # optional config reads, best-effort push/pull) explicitly expect
        # empty-string as a "not available" sentinel and handle it at the
        # call site. Do not remove this path without converting all callers
        # to try/except.
    """
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=check,
            timeout=30,  # writing-code:15: bounded git wait
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            raise GitError(f"Git command failed: {' '.join(args)} - {e.stderr}") from e
        return ""  # SU-1: intentional — callers must handle
