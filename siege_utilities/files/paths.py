import pathlib
import zipfile
import logging
logger = logging.getLogger(__name__)


def ensure_path_exists(desired_path: pathlib.Path) ->pathlib.Path:
    """""\"
Perform file operations: ensure path exists.

Part of Siege Utilities File Operations module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.ensure_path_exists()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    try:
        desired_path_object = pathlib.Path(desired_path)
        result = pathlib.Path(desired_path_object).mkdir(parents=True,
            exist_ok=True)
        message = f'Generated a path at {str(desired_path_object)}: {result}'
        log_info(message=message)
        gitkeep_file = desired_path_object / '.gitkeep'
        delete_existing_file_and_replace_it_with_an_empty_file(gitkeep_file)
        log_info(message=message)
        return desired_path_object
    except Exception as e:
        message = f'Exception while generating local path: {e}'
        log_error(message=message)
        return False


def unzip_file_to_its_own_directory(path_to_zipfile: pathlib.Path,
    new_dir_name=None, new_dir_parent=None):
    """""\"
Perform file operations: unzip file to its own directory.

Part of Siege Utilities File Operations module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.unzip_file_to_its_own_directory()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    try:
        path_to_zipfile = pathlib.Path(path_to_zipfile)
        frtz = zipfile.ZipFile(path_to_zipfile)
        if new_dir_name is None:
            new_dir_name = path_to_zipfile.stem
        if new_dir_parent is None:
            new_dir_parent = path_to_zipfile.parent
        target_dir_for_unzipped_files = new_dir_parent / new_dir_name
        pathlib.Path(target_dir_for_unzipped_files).mkdir(parents=True,
            exist_ok=True)
        frtz.extractall(path=target_dir_for_unzipped_files)
        message = (
            f'Just unzipped: \n {path_to_zipfile} \n To: {target_dir_for_unzipped_files}'
            )
        log_info(message=message)
        return target_dir_for_unzipped_files
    except Exception as e:
        message = f'There was an error: {e}'
        log_error(message=message)
        return False
