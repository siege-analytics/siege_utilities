# Python stdlib

import subprocess
import logging

logger = logging.getLogger(__name__)


def run_subprocess(command_list):
    """
    Run a shell command as a subprocess and handle the output.

    Args:
        command_list: The command to run, as a list or string

    Returns:
        The command output (stdout if successful, stderr if failed)
    """
    # Execute the command
    p = subprocess.Popen(
        command_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    stdout, stderr = p.communicate()
    returncode = p.returncode

    if returncode != 0:
        output = stderr.decode("utf-8")
        message = f"Subprocess {command_list} failed with return code {returncode}. "
        message += f"stderr: {output}"
        log_error(message=message)
        return output
    else:
        output = stdout.decode("utf-8")
        message = f"Subprocess {command_list} completed with return code {returncode}. "
        message += f"stdout: {output}"
        log_info(message=message)
        return output


# These next few functions can be done using Python methods or command line tools
# The first two are the Python variants
