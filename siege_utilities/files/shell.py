"""Execute argv commands with an allow-list and conservative argument checks.

These checks are a guardrail, not a sandbox or a guarantee of read-only behavior.
"""

import os
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
    pass


# Command names are restricted; their options are not exhaustively validated.
ALLOWED_COMMANDS = {
    'ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'wc', 'grep',
    'which', 'whoami', 'date', 'hostname', 'uname'
}


def validate_command_safety(command: Union[str, List[str]],
                            allow_list: Optional[set] = None) -> List[str]:
    """
    Apply command-name, character, traversal, and known sensitive-path checks.

    Arguments are checked using expanded, normalized and resolved path forms,
    but returned unchanged. This is not a filesystem sandbox: command options,
    recursive reads and filesystem changes after validation are not controlled.
    A custom allow-list delegates command semantics to the caller.

    Parameters
    ----------
    command : str or list[str]
        Command string or argv list to validate.
    allow_list : set, optional
        Custom allowed command names, replacing the default allow-list.

    Returns
    -------
    list[str]
        Validated argv with argument text unchanged.

    Raises
    ------
    SecurityError
        If the command contains forbidden elements.
    ValueError
        If the command is empty or has invalid quoting.

    Notes
    -----
    - Validates command against whitelist
    - Rejects selected shell metacharacters, including redirection characters
    - Rejects '..' path components
    - Rejects known sensitive paths and .ssh path components, including aliases
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
            raise ValueError(f"Invalid command syntax: {e}") from e
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
    dangerous_chars = [';', '&', '|', '$', '`', '\n', '\r', '(', ')', '<', '>']
    sensitive_paths = ['/etc/passwd', '/etc/shadow', '/etc/sudoers',
                       '~/.ssh', '/root', '/var/log']
    sensitive_forms = {
        form
        for path in sensitive_paths
        for form in (os.path.normpath(os.path.expanduser(path)),
                     os.path.realpath(os.path.expanduser(path)))
    }

    for part in parts:
        # Check for command injection characters
        for char in dangerous_chars:
            if char in part:
                raise SecurityError(
                    f"Forbidden character '{char}' in command component: {part}"
                )

        # Check both lexical and resolved forms so symlinks cannot hide a path.
        # Also inspect --option=path values without treating the option as a path.
        path_values = [part, part.split('=', 1)[-1]]
        for path in path_values:
            expanded = os.path.expanduser(path)
            forms = (os.path.normpath(expanded), os.path.realpath(expanded))
            if any('.ssh' in form.split(os.sep) or
                   any(form == sensitive or form.startswith(sensitive + os.sep)
                       for sensitive in sensitive_forms)
                   for form in forms):
                raise SecurityError(
                    f"Access to sensitive path forbidden: {part}"
                )
            if '..' in path.replace(os.sep, '/').split('/'):
                raise SecurityError(f"Path traversal detected: {part}")

    return parts


def run_subprocess(command_list: Union[str, List[str]],
                  allow_list: Optional[set] = None,
                  timeout: int = 30) -> str:
    """
    Run an argv command after applying validate_command_safety.

    Execution uses shell=False, so shell syntax is not interpreted. Validation
    restricts command names and selected argument patterns; it does not promise
    read-only behavior or exhaustive validation of each program's options.

    Parameters
    ----------
    command_list : str or list[str]
        Command string or argv list to run.
    allow_list : set, optional
        Custom allowed command names, replacing the default allow-list.
    timeout : int, default 30
        Command timeout in seconds.

    Returns
    -------
    str
        The command output (stdout if successful, stderr if failed, with an
        error logged for a nonzero exit status).

    Raises
    ------
    SecurityError
        If the command fails validation.
    ValueError
        If the command is invalid.
    subprocess.TimeoutExpired
        If the command times out.
    OSError
        If the command cannot be executed.

    Examples
    --------
    >>> output = run_subprocess("ls -la")  # doctest: +SKIP

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
        except subprocess.TimeoutExpired as e:
            p.kill()
            stdout, stderr = p.communicate()
            raise subprocess.TimeoutExpired(
                validated_command, timeout,
                output=stdout, stderr=stderr
            ) from e

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
    except OSError as e:
        log_error(f"Command execution failed: {e}")
        raise


__all__ = [
    'run_subprocess',
    'validate_command_safety',
    'SecurityError',
    'ALLOWED_COMMANDS'
]
