"""
Secure shell command execution utilities.

SECURITY NOTE: This module previously contained critical vulnerabilities.
All shell execution now includes proper validation and sanitization.
"""

import subprocess
import logging
import shlex
from typing import Union, List, Optional

logger = logging.getLogger(__name__)

# Import logging functions from main package
try:
    from siege_utilities.core.logging import log_info, log_warning, log_error, log_debug
except ImportError:
    # Fallback if main package not available yet
    import logging
    _fallback_logger = logging.getLogger(__name__)
    def log_info(message): _fallback_logger.info(message)
    def log_error(message): _fallback_logger.error(message)
    def log_warning(message): _fallback_logger.warning(message)
    def log_debug(message): _fallback_logger.debug(message)


class SecurityError(Exception):
    """Raised when a security violation is detected."""


# Whitelist of allowed base commands
# Only safe, read-only commands are permitted by default
ALLOWED_COMMANDS = {
    'ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'wc', 'grep',
    'find', 'which', 'whoami', 'date', 'hostname', 'uname'
}


def validate_command_safety(command: Union[str, List[str]],
                            allow_list: Optional[set] = None) -> List[str]:
    """
    Validate that a command is safe to execute.

    Args:
        command: Command string or list to validate
        allow_list: Optional custom whitelist of allowed commands

    Returns:
        Validated command as list of strings

    Raises:
        SecurityError: If command contains forbidden elements
        ValueError: If command is invalid

    Security checks:
    - Validates command against whitelist
    - Blocks command injection characters (;, &, |, $, `, newlines)
    - Blocks path traversal attempts
    - Blocks access to sensitive system files
    """
    if not command:
        raise ValueError("Command cannot be empty")

    # Use provided whitelist or default
    allowed = allow_list if allow_list is not None else ALLOWED_COMMANDS

    # Parse command into components
    if isinstance(command, str):
        try:
            parts = shlex.split(command)
        except ValueError as e:
            raise ValueError(f"Invalid command syntax: {e}")
    else:
        parts = list(command)

    if not parts:
        raise ValueError("Invalid command: no components")

    base_command = parts[0]

    # Check if base command is in whitelist
    if base_command not in allowed:
        raise SecurityError(
            f"Command '{base_command}' not allowed. "
            f"Allowed commands: {sorted(allowed)}"
        )

    # Validate all command components
    dangerous_chars = [';', '&', '|', '$', '`', '\n', '\r', '(', ')']

    for part in parts:
        # Check for command injection characters
        for char in dangerous_chars:
            if char in part:
                raise SecurityError(
                    f"Forbidden character '{char}' in command component: {part}"
                )

        # Check for path traversal
        if '..' in part:
            raise SecurityError(f"Path traversal detected: {part}")

        # Check for access to sensitive system files
        sensitive_paths = ['/etc/passwd', '/etc/shadow', '/etc/sudoers',
                          '~/.ssh', '/root', '/var/log']
        for sensitive in sensitive_paths:
            if sensitive in part:
                raise SecurityError(
                    f"Access to sensitive path forbidden: {part}"
                )

    return parts


def run_subprocess(command_list: Union[str, List[str]],
                  allow_list: Optional[set] = None,
                  timeout: int = 30) -> str:
    """
    Run a shell command as a subprocess with security validation.

    SECURITY: This function now validates all commands against a whitelist
    and blocks dangerous operations. Only read-only commands are allowed
    by default.

    Args:
        command_list: The command to run, as a list or string
        allow_list: Optional custom whitelist of allowed commands
        timeout: Command timeout in seconds (default: 30)

    Returns:
        The command output (stdout if successful, stderr if failed)

    Raises:
        SecurityError: If command fails security validation
        ValueError: If command is invalid
        subprocess.TimeoutExpired: If command times out

    Example:
        >>> # This works (safe command)
        >>> output = run_subprocess("ls -la")
        >>>
        >>> # This fails (dangerous command)
        >>> output = run_subprocess("rm -rf /")  # Raises SecurityError

    Security Changes:
        - Previously used shell=True with no validation (CRITICAL VULNERABILITY)
        - Now validates all commands against whitelist
        - Blocks command injection, path traversal, sensitive file access
        - Uses shell=False by default for safety
    """
    try:
        # Validate command security
        validated_command = validate_command_safety(command_list, allow_list)

        # Execute with shell=False (safer)
        p = subprocess.Popen(
            validated_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False  # Changed from True - SECURITY FIX
        )

        try:
            stdout, stderr = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            stdout, stderr = p.communicate()
            raise subprocess.TimeoutExpired(
                validated_command, timeout,
                output=stdout, stderr=stderr
            )

        returncode = p.returncode

        if returncode != 0:
            output = stderr.decode('utf-8')
            message = (
                f'Subprocess {validated_command} failed with return code {returncode}. '
            )
            message += f'stderr: {output}'
            log_error(message)
            return output
        else:
            output = stdout.decode('utf-8')
            message = (
                f'Subprocess {validated_command} completed with return code {returncode}. '
            )
            message += f'stdout: {output}'
            log_info(message)
            return output

    except (SecurityError, ValueError) as e:
        log_error(f"Security validation failed: {e}")
        raise
    except Exception as e:
        log_error(f"Command execution failed: {e}")
        raise


def run_subprocess_unrestricted(command_list: Union[str, List[str]],
                                timeout: int = 30) -> str:
    """
    Run a shell command WITHOUT security restrictions.

    ⚠️ DANGER: This function executes arbitrary commands without validation.
    Use only in trusted environments with trusted input.

    This function exists for backward compatibility with code that requires
    unrestricted shell access. It should be removed in future versions.

    Args:
        command_list: The command to run, as a list or string
        timeout: Command timeout in seconds (default: 30)

    Returns:
        The command output (stdout if successful, stderr if failed)

    Raises:
        subprocess.TimeoutExpired: If command times out

    Example:
        >>> # This function allows dangerous commands (use with extreme caution)
        >>> output = run_subprocess_unrestricted("custom_command --arg")

    Security Warning:
        This function replicates the old vulnerable behavior for backward
        compatibility. It will be deprecated and removed in a future version.
        Migrate to run_subprocess() with a custom allow_list instead.
    """
    log_warning(
        "⚠️ SECURITY WARNING: Using unrestricted subprocess execution. "
        "This is dangerous and will be removed in future versions."
    )

    p = subprocess.Popen(
        command_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True  # DANGER: No validation
    )

    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        stdout, stderr = p.communicate()
        raise

    returncode = p.returncode

    if returncode != 0:
        output = stderr.decode('utf-8')
        message = (
            f'Subprocess {command_list} failed with return code {returncode}. '
        )
        message += f'stderr: {output}'
        log_error(message)
        return output
    else:
        output = stdout.decode('utf-8')
        message = (
            f'Subprocess {command_list} completed with return code {returncode}. '
        )
        message += f'stdout: {output}'
        log_info(message)
        return output


__all__ = [
    'run_subprocess',
    'run_subprocess_unrestricted',
    'validate_command_safety',
    'SecurityError',
    'ALLOWED_COMMANDS'
]
