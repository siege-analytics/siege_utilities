"""
Fixed HDFS Operations - Minimal working version
"""
import os
import subprocess
import pathlib
import json
import time
import hashlib
from typing import Optional, Tuple, Dict

from siege_utilities.core.logging import get_logger, log_info, log_warning, log_error, log_debug


def get_quick_file_signature(file_path):
    """""\"
Perform file operations: get quick file signature.

Part of Siege Utilities File Operations module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.get_quick_file_signature()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    try:
        stat = pathlib.Path(file_path).stat()
        return f'{stat.st_size}_{stat.st_mtime}'
    except:
        return 'error'


def check_hdfs_status():
    """Check if HDFS is accessible"""
    try:
        result = subprocess.run(['hdfs', 'dfs', '-ls', '/'], capture_output
            =True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False
