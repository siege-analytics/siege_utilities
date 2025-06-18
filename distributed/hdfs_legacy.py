#!/usr/bin/env python3
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

def log_info(msg):
    print(f"INFO: {msg}")

def log_error(msg):
    print(f"ERROR: {msg}")

# Minimal fallback hash function
def get_quick_file_signature(file_path):
    try:
        stat = pathlib.Path(file_path).stat()
        return f"{stat.st_size}_{stat.st_mtime}"
    except:
        return "error"

def check_hdfs_status():
    """Check if HDFS is accessible"""
    try:
        result = subprocess.run(
            ["hdfs", "dfs", "-ls", "/"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except:
        return False
