"""
Git input validation and sanitization utilities.

This module provides security-focused input validation for git operations to prevent:
- Command injection in git commands
- Invalid/malicious branch names, tag names, commit messages
- Path traversal in repository paths
- Dangerous git command patterns

Use these validators in all git operations to ensure secure command execution.
"""

import re
import logging
from pathlib import Path

# Get logger for this module
log = logging.getLogger(__name__)


class GitSecurityError(Exception):
    """Raised when git input fails security validation."""


# Dangerous characters in git inputs
DANGEROUS_GIT_CHARS = {
    ';',   # Command separator
    '&',   # Background/chain
    '|',   # Pipe
    '$',   # Variable expansion
    '`',   # Command substitution
    '(',   # Subshell
    ')',   # Subshell
    '<',   # Redirection
    '>',   # Redirection
    '\n',  # Newline
    '\r',  # Carriage return
    '\x00', # Null byte
}


# Git ref name rules (from git-check-ref-format)
# See: https://git-scm.com/docs/git-check-ref-format
GIT_REF_INVALID_PATTERNS = [
    r'\.\.',           # No ..
    r'@{',             # No @{
    r'/\.',            # No component starting with .
    r'\.$',            # No ending with .
    r'\.lock$',        # No ending with .lock
    r'^/',             # No starting with /
    r'/$',             # No ending with /
    r'//',             # No consecutive slashes
    r'\*',             # No asterisk
    r'\?',             # No question mark
    r'\[',             # No open bracket
    r'\\',             # No backslash
    r'\^',             # No caret
    r'~',              # No tilde
    r':',              # No colon
    r' ',              # No spaces
]


def has_dangerous_characters(text: str) -> bool:
    """
    Check if text contains characters dangerous for git commands.

    Args:
        text: Text to check

    Returns:
        True if text contains dangerous characters

    Example:
        >>> has_dangerous_characters("branch-name")
        False
        >>> has_dangerous_characters("branch; rm -rf /")
        True
    """
    for char in DANGEROUS_GIT_CHARS:
        if char in text:
            return True
    return False


def validate_git_ref_name(ref_name: str, ref_type: str = "ref") -> str:
    """
    Validate a git reference name (branch, tag, remote).

    Implements git-check-ref-format rules:
    - No path component starting with .
    - No double dots ..
    - No ASCII control characters, space, ~, ^, :, ?, *, [
    - No ending with /
    - No ending with .lock
    - No @ with { following it
    - No backslashes

    Args:
        ref_name: Reference name to validate
        ref_type: Type of reference (branch, tag, remote) for error messages

    Returns:
        Validated reference name

    Raises:
        GitSecurityError: If ref name fails validation
        ValueError: If ref name is invalid

    Example:
        >>> validate_git_ref_name("feature/my-branch", "branch")
        'feature/my-branch'
        >>>
        >>> validate_git_ref_name("branch; rm -rf /", "branch")
        Raises GitSecurityError
    """
    if not ref_name:
        raise ValueError(f"Git {ref_type} name cannot be empty")

    # Check for dangerous command injection characters
    if has_dangerous_characters(ref_name):
        raise GitSecurityError(
            f"Git {ref_type} name contains dangerous characters: {ref_name}"
        )

    # Check against invalid patterns
    for pattern in GIT_REF_INVALID_PATTERNS:
        if re.search(pattern, ref_name):
            raise GitSecurityError(
                f"Git {ref_type} name contains invalid pattern '{pattern}': {ref_name}"
            )

    # Must not be empty after stripping
    if not ref_name.strip():
        raise ValueError(f"Git {ref_type} name cannot be whitespace only")

    # Additional checks for specific characters
    if ref_name.startswith('-'):
        raise GitSecurityError(
            f"Git {ref_type} name cannot start with '-': {ref_name}"
        )

    log.debug(f"Git {ref_type} name validated: {ref_name}")
    return ref_name


def validate_branch_name(branch_name: str) -> str:
    """
    Validate a git branch name.

    Args:
        branch_name: Branch name to validate

    Returns:
        Validated branch name

    Raises:
        GitSecurityError: If branch name fails validation

    Example:
        >>> validate_branch_name("feature/authentication")
        'feature/authentication'
        >>>
        >>> validate_branch_name("branch$(cat /etc/passwd)")
        Raises GitSecurityError
    """
    return validate_git_ref_name(branch_name, "branch")


def validate_tag_name(tag_name: str) -> str:
    """
    Validate a git tag name.

    Args:
        tag_name: Tag name to validate

    Returns:
        Validated tag name

    Raises:
        GitSecurityError: If tag name fails validation

    Example:
        >>> validate_tag_name("v1.0.0")
        'v1.0.0'
        >>>
        >>> validate_tag_name("<script>alert('xss')</script>")
        Raises GitSecurityError
    """
    return validate_git_ref_name(tag_name, "tag")


def validate_commit_message(message: str, max_length: int = 10000) -> str:
    """
    Validate a git commit message.

    Args:
        message: Commit message to validate
        max_length: Maximum allowed length

    Returns:
        Validated commit message

    Raises:
        GitSecurityError: If message fails validation
        ValueError: If message is invalid

    Example:
        >>> validate_commit_message("Fix bug in authentication")
        'Fix bug in authentication'
        >>>
        >>> validate_commit_message("Message; rm -rf /")
        Raises GitSecurityError
    """
    if not message:
        raise ValueError("Commit message cannot be empty")

    # Check length
    if len(message) > max_length:
        raise ValueError(f"Commit message too long: {len(message)} > {max_length}")

    # Check for dangerous command injection characters
    # Note: Newlines are OK in commit messages, but other dangerous chars are not
    dangerous_chars = DANGEROUS_GIT_CHARS - {'\n', '\r'}
    for char in dangerous_chars:
        if char in message:
            raise GitSecurityError(
                f"Commit message contains dangerous character '{char}'"
            )

    # Check for null bytes
    if '\x00' in message:
        raise GitSecurityError("Commit message contains null byte")

    log.debug(f"Commit message validated ({len(message)} chars)")
    return message


def validate_commit_hash(commit_hash: str) -> str:
    """
    Validate a git commit hash (SHA).

    Args:
        commit_hash: Commit hash to validate (short or full)

    Returns:
        Validated commit hash

    Raises:
        GitSecurityError: If commit hash fails validation
        ValueError: If commit hash is invalid

    Example:
        >>> validate_commit_hash("a1b2c3d")
        'a1b2c3d'
        >>>
        >>> validate_commit_hash("abc123; rm -rf /")
        Raises GitSecurityError
    """
    if not commit_hash:
        raise ValueError("Commit hash cannot be empty")

    # Check for dangerous characters
    if has_dangerous_characters(commit_hash):
        raise GitSecurityError(
            f"Commit hash contains dangerous characters: {commit_hash}"
        )

    # Must be alphanumeric only
    if not re.match(r'^[a-fA-F0-9]+$', commit_hash):
        raise ValueError(
            f"Commit hash must be hexadecimal: {commit_hash}"
        )

    # Check length (short hash is typically 7+, full is 40)
    if len(commit_hash) < 4 or len(commit_hash) > 40:
        raise ValueError(
            f"Commit hash length invalid: {len(commit_hash)} (expected 4-40)"
        )

    log.debug(f"Commit hash validated: {commit_hash}")
    return commit_hash


def validate_remote_name(remote_name: str) -> str:
    """
    Validate a git remote name.

    Args:
        remote_name: Remote name to validate (e.g., "origin")

    Returns:
        Validated remote name

    Raises:
        GitSecurityError: If remote name fails validation

    Example:
        >>> validate_remote_name("origin")
        'origin'
        >>>
        >>> validate_remote_name("origin; curl evil.com")
        Raises GitSecurityError
    """
    if not remote_name:
        raise ValueError("Remote name cannot be empty")

    # Check for dangerous characters
    if has_dangerous_characters(remote_name):
        raise GitSecurityError(
            f"Remote name contains dangerous characters: {remote_name}"
        )

    # Must be alphanumeric, hyphens, underscores only
    if not re.match(r'^[a-zA-Z0-9_-]+$', remote_name):
        raise GitSecurityError(
            f"Remote name contains invalid characters: {remote_name}"
        )

    log.debug(f"Remote name validated: {remote_name}")
    return remote_name


def validate_repo_path(repo_path: str) -> Path:
    """
    Validate a repository path.

    Args:
        repo_path: Repository path to validate

    Returns:
        Validated Path object

    Raises:
        GitSecurityError: If path fails security validation

    Example:
        >>> validate_repo_path(".")
        PosixPath('.')
        >>>
        >>> validate_repo_path("../../../etc")
        Raises GitSecurityError
    """
    # Import path validation
    try:
        from siege_utilities.files.validation import validate_directory_path, PathSecurityError
    except ImportError:
        # Fallback: basic validation
        log.warning("Path validation module not available - using basic validation")
        return Path(repo_path)

    try:
        validated_path = validate_directory_path(repo_path, must_exist=False)
        return validated_path
    except PathSecurityError as e:
        raise GitSecurityError(f"Repository path validation failed: {e}")


__all__ = [
    'GitSecurityError',
    'validate_branch_name',
    'validate_tag_name',
    'validate_commit_message',
    'validate_commit_hash',
    'validate_remote_name',
    'validate_repo_path',
    'has_dangerous_characters',
]
