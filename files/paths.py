# Python stdlib

import io
import hashlib
from pyexpat.errors import messages

from IPython.utils.capture import capture_output
import pathlib
import requests
import subprocess

from pkg_resources import working_set
from tqdm import tqdm

import zipfile

# Logging

import logging

from siege_siege_utilities.core.logging import *
from siege_siege_utilities.files.operations import *

logging.getLogger(__name__)


def ensure_path_exists(desired_path: pathlib.Path) -> pathlib.Path:

    try:
        desired_path_object = pathlib.Path(desired_path)
        result = pathlib.Path(desired_path_object).mkdir(parents=True, exist_ok=True)
        message = f"Generated a path at {str(desired_path_object)}: {result}"
        log_info(message=message)
        gitkeep_file = desired_path_object / ".gitkeep"
        delete_existing_file_and_replace_it_with_an_empty_file(gitkeep_file)
        log_info(message=message)

        return desired_path_object

    except Exception as e:
        message = f"Exception while generating local path: {e}"
        log_error(message=message)
        return False


def unzip_file_to_its_own_directory(
    path_to_zipfile: pathlib.Path, new_dir_name=None, new_dir_parent=None
):
    try:
        path_to_zipfile = pathlib.Path(path_to_zipfile)
        frtz = zipfile.ZipFile(path_to_zipfile)
        if new_dir_name is None:
            new_dir_name = path_to_zipfile.stem
        if new_dir_parent is None:
            new_dir_parent = path_to_zipfile.parent

        # ensure that a directory exists for the new files to go in
        target_dir_for_unzipped_files = new_dir_parent / new_dir_name

        pathlib.Path(target_dir_for_unzipped_files).mkdir(parents=True, exist_ok=True)

        frtz.extractall(path=target_dir_for_unzipped_files)
        message = f"Just unzipped: \n {path_to_zipfile} \n To: {target_dir_for_unzipped_files}"
        log_info(message=message)
        return target_dir_for_unzipped_files

    except Exception as e:

        message = f"There was an error: {e}"
        log_error(message=message)
        return False
