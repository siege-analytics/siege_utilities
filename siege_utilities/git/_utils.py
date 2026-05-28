"""Shared internal helpers for the git sub-package."""

import subprocess

from siege_utilities.exceptions import GitError


def run_git_command(*args, repo_path: str = ".", check: bool = True) -> str:
    """Run a git command and return stdout.

    When ``check=True`` (default), raises ``GitError`` on non-zero exit.
    When ``check=False``, returns ``""`` on failure — callers must treat
    empty string as a potential error signal, not as valid empty output.
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
        return ""
