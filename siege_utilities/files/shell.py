import subprocess
import logging
logger = logging.getLogger(__name__)

# Import logging functions from main package
try:
    from siege_utilities import log_info, log_error
except ImportError:
    # Fallback if main package not available yet
    def log_info(message): print(f"INFO: {message}")
    def log_error(message): print(f"ERROR: {message}")


def run_subprocess(command_list):
    """
    Run a shell command as a subprocess and handle the output.

    Args:
        command_list: The command to run, as a list or string

    Returns:
        The command output (stdout if successful, stderr if failed)
    """
    p = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=
        subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
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
