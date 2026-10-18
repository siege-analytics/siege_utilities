"""Execute argv commands with an allow-list and conservative argument checks.

These checks are a guardrail, not a sandbox or a guarantee of read-only behavior.
"""

import os
import subprocess
import logging
import shlex
from typing import Union, List, Optional

from siege_utilities.core._sensitive_paths import ROOT_CREDENTIAL_STORES

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

# The shell policy always blocks /root and /var/log, without the file policy's
# containment carve-outs. Shadow prefixes and process-relative /proc checks
# remain separate below; /dev has no blanket ban here.
_SHELL_SENSITIVE_PATH_ADDITIONS = {
    '/etc/passwd', '/etc/passwd-', '/etc/shadow-',
    '/etc/gshadow', '/etc/gshadow-', '/etc/sudoers', '/etc/sudoers.d',
    '~/.ssh', '/root', '/var/log',
}
SENSITIVE_PATHS = _SHELL_SENSITIVE_PATH_ADDITIONS | ROOT_CREDENTIAL_STORES


# /proc/<pid>/<entry> links whose target depends on which process opens them.
# The validator runs in the parent, so it cannot resolve them as the child will.
_PROC_CONTEXT_ENTRIES = frozenset({'cwd', 'root', 'fd', 'task', 'map_files'})


def _crosses_proc_context_link(path: str, max_hops: int = 40) -> bool:
    """Return True if resolving path enters /proc/<pid>/{cwd,root,fd,task,map_files}."""
    pending = [c for c in path.split(os.sep) if c]
    current = os.sep
    hops = 0
    while pending:
        component = pending.pop(0)
        if component == '.':
            continue
        if component == '..':
            current = os.path.dirname(current)
            continue
        candidate = os.path.join(current, component)
        segments = candidate.split(os.sep)
        if len(segments) >= 4 and segments[1] == 'proc' and segments[3] in _PROC_CONTEXT_ENTRIES:
            return True
        if os.path.islink(candidate):
            hops += 1
            if hops > max_hops:
                return True
            try:
                target = os.readlink(candidate)
            except OSError:
                return True
            pending = [c for c in target.split(os.sep) if c] + pending
            if target.startswith(os.sep):
                current = os.sep
            continue
        current = candidate
    return False


def validate_command_safety(command: Union[str, List[str]],
                            allow_list: Optional[set] = None,
                            cwd: str | os.PathLike[str] | None = None) -> List[str]:
    """
    Apply command-name, character, traversal, and known sensitive-path checks.

    Operands and attached option values are checked using literal, expanded,
    normalized and resolved path forms relative to cwd, but returned unchanged.
    Process-relative /proc links (/proc/<pid>/cwd, root, fd, task, map_files)
    are rejected because they resolve differently in the child.
    This is not a filesystem sandbox: command options,
    recursive reads and filesystem changes after validation are not controlled.
    A custom allow-list delegates command semantics to the caller.

    Parameters
    ----------
    command : str or list[str]
        Command string or argv list to validate.
    allow_list : set, optional
        Custom allowed command names, replacing the default allow-list.
    cwd : str or os.PathLike, optional
        Working directory used for execution and relative path checks.
        Defaults to the current process directory.

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
    sensitive_forms = {
        form
        for path in SENSITIVE_PATHS
        for form in (os.path.normpath(os.path.expanduser(path)),
                     os.path.realpath(os.path.expanduser(path)))
    }
    # Shadow databases and their sibling backups share these filename prefixes.
    sensitive_prefixes = tuple(
        form
        for path in ('/etc/shadow', '/etc/gshadow')
        for form in (os.path.normpath(path), os.path.realpath(path))
    )
    base_directory = os.getcwd() if cwd is None else os.path.abspath(os.path.expanduser(cwd))

    for part in parts:
        # Check for command injection characters
        for char in dangerous_chars:
            if char in part:
                raise SecurityError(
                    f"Forbidden character '{char}' in command component: {part}"
                )

        # Check both lexical and resolved forms so symlinks cannot hide a path.
        # A short-option value can begin after any letter in a getopt cluster.
        path_values = [part, part.split('=', 1)[-1]]
        if part.startswith('-') and not part.startswith('--'):
            path_values.extend(part[k:] for k in range(2, len(part)))
        for path in path_values:
            for spelling in dict.fromkeys((path, os.path.expanduser(path))):
                expanded = os.path.join(base_directory, spelling)
                if _crosses_proc_context_link(expanded):
                    raise SecurityError(
                        f"Access to sensitive path forbidden: {part}"
                    )
                forms = (os.path.normpath(expanded), os.path.realpath(expanded))
                if any('.ssh' in form.split(os.sep) or
                       form.startswith(sensitive_prefixes) or
                       (form.startswith('/proc/') and form.endswith(('/environ', '/cmdline'))) or
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
        error logged for a nonzero exit status). Arguments and output are
        omitted from logs. Raised diagnostics omit command details and
        captured output, which may contain credentials.

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
        except subprocess.TimeoutExpired:
            p.kill()
            stdout, stderr = p.communicate()
            log_error("Subprocess timed out (arguments and output omitted)")
            raise subprocess.TimeoutExpired(
                '[REDACTED]', timeout,
            ) from None

        returncode = p.returncode

        if returncode != 0:
            output = stderr.decode('utf-8')
            message = (
                f'Subprocess failed with return code {returncode} (arguments and output omitted)'
            )
            log_error(message)
            return output
        else:
            output = stdout.decode('utf-8')
            message = (
                f'Subprocess completed with return code {returncode} (arguments and output omitted)'
            )
            log_info(message)
            return output

    except SecurityError:
        log_error("Security validation failed (command omitted)")
        raise SecurityError('Security validation failed (command redacted)') from None
    except ValueError:
        log_error("Invalid command or output (details omitted)")
        raise ValueError('Invalid command or output (details redacted)') from None
    except OSError as e:
        log_error("Command execution failed (details omitted)")
        raise OSError(e.errno, 'Command execution failed (details redacted)') from None


__all__ = [
    'run_subprocess',
    'validate_command_safety',
    'SecurityError',
    'ALLOWED_COMMANDS'
]
