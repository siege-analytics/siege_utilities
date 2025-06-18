import pathlib
import subprocess
import logging
logger = logging.getLogger(__name__)


def rmtree(f: pathlib.Path):
    """""\"
Utility function: rmtree.

Part of Siege Utilities Utilities module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.rmtree()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    if f.is_file():
        f.unlink()
    else:
        for child in f.iterdir():
            rmtree(child)
        f.rmdir()


def check_if_file_exists_at_path(target_file_path: pathlib.Path) ->bool:
    """

    :param target_file_path: This is the path we are going to check to see if a file exists
    :return: True if file exists, False otherwise
    """
    message = f'Check if file exists at path: {target_file_path} '
    log_info(message)
    target_file_path = pathlib.Path(target_file_path)
    if target_file_path.exists():
        message = (
            f'The file at path {target_file_path} exists, so it will return True'
            )
        log_info(message=message)
        return True
    else:
        message = (
            f'The file at path {target_file_path} does not exist, so it will return False'
            )
        log_info(message=message)
        return False


def delete_existing_file_and_replace_it_with_an_empty_file(target_file_path:
    pathlib.Path) ->pathlib.Path:
    """
    This function deletes the existing file and replaces it with an empty file.
    :param target_file_path: Pathlib.path object to interact with
    :return: pathlib.Path object to interact with
    """
    target_file_path_as_string = str(target_file_path)
    working_target_file_path = pathlib.Path(target_file_path)
    message = (
        f'Going to delete existing file {target_file_path} and replace it with an empty file.'
        )
    log_info(message=message)
    if working_target_file_path.exists():
        message += (
            f'There is an existing file, we have to delete {target_file_path_as_string}\n'
            )
        log_info(message=message)
        working_target_file_path.unlink()
        message = f'Deleted {working_target_file_path}\n'
        log_info(message=message)
    else:
        message = (
            f'{target_file_path_as_string} does not exist, no need to delete')
        log_info(message=message)
    message = f'About to replace {working_target_file_path}\n'
    log_info(message=message)
    working_target_file_path.parent.mkdir(exist_ok=True, parents=True)
    working_target_file_path.touch(exist_ok=False)
    message = f'Created {working_target_file_path}\n'
    log_info(message=message)
    return working_target_file_path


def count_total_rows_in_file_pythonically(target_file_path: pathlib.Path
    ) ->int:
    """
    :param target_file_path: pathlib.Path object that we are going to count the rows of
    :return: count of total rows in file
    """
    with open(target_file_path, 'rb') as f:
        total_rows_count = sum(1 for line in target_file_path)
    return total_rows_count


def count_empty_rows_in_file_pythonically(target_file_path: pathlib.Path
    ) ->int:
    """

    :param target_file_path: pathlib.Path object that we are going to count the empty rows of
    :return: count of empty rows in file
    """
    with open(target_file_path, 'r') as f:
        total_empty_rows_count = sum(1 for line in target_file_path if len(
            line.strip()) < 1)
    return total_empty_rows_count


def count_duplicate_rows_in_file_using_awk(target_file_path: pathlib.Path
    ) ->int:
    """
    "This uses an awk pattern from Justin Hernandez to count duplicate rows in file"
    :param target_file_path: pathlib.Path object that we are going to count the duplicate rows of
    :return: count of duplicate rows in file
    """
    message = (
        f'In the count duplicate rows using awk function for {target_file_path}\n'
        )
    logger.info(message)
    awk_template = (
        f"awk '_[$0]++' {target_file_path} | sed '/^[[:space:]]*$/d' | wc -l")
    command = awk_template
    result = subprocess.run(command, shell=True, capture_output=True, text=True
        )
    if result.stderr == None:
        error_code = 'None'
    else:
        error_code = result.stderr
    message = (
        f'Ran awk on {target_file_path}, result is {result.stdout}, error code is {error_code}'
        )
    subprocess_command_output = str(result.stdout)
    if result.returncode == 0:
        if len(subprocess_command_output) < 1:
            message = (
                f'The duplicate rows awk command did not return any output: {subprocess_command_output}'
                )
            log_info(message)
            duplicate_rows_count = 0
        else:
            message = (
                f'The duplicate rows awk command returned {subprocess_command_output}'
                )
            log_info(message)
            duplicate_rows_count = int(subprocess_command_output)
        message = (
            f'SUCCESS: Found {duplicate_rows_count} duplicate rows in file {target_file_path}, returning to memory'
            )
        log_info(message)
        return duplicate_rows_count
    else:
        message = (
            f'There was an error counting duplicate rows in {target_file_path}: {result.stderr}'
            )
        logger.error(message)
        return duplicate_rows_count


def count_total_rows_in_file_using_sed(target_file_path: pathlib.Path) ->int:
    """
    :param target_file_path: pathlib.Path object that we are going to count the total rows of
    :return: count of total rows in file
    """
    message = (
        f'In the count total rows using sed function for {target_file_path}\n')
    log_info(message)
    sed_template = f"sed -n '$=' {target_file_path}"
    command = sed_template
    result = subprocess.run(command, shell=True, capture_output=True, text=True
        )
    if result.stderr is None:
        error_code = 'None'
    else:
        error_code = result.stderr
    message = (
        f'Ran sed on {target_file_path}, result is {result.stdout}, error code is {error_code}'
        )
    subprocess_command_output = str(result.stdout)
    if result.returncode == 0:
        if len(subprocess_command_output
            ) < 1 or subprocess_command_output == '\n':
            message = (
                f'The total rows sed command returned no output {subprocess_command_output}'
                )
            log_info(message)
            total_rows_count = 0
        else:
            message = (
                f'The total rows sed command returned {subprocess_command_output}'
                )
            log_info(message)
            total_rows_count = int(subprocess_command_output)
        message = (
            f'SUCCESS: Found {total_rows_count} total rows in file {target_file_path}, returning to memory'
            )
        log_info(message)
        return total_rows_count
    else:
        total_rows_count = False
        message = (
            f'There was an error counting total rows in {target_file_path}: {result.stderr}'
            )
        log_error(message)
        return total_rows_count


def count_empty_rows_in_file_using_awk(target_file_path: pathlib.Path) ->int:
    """
    :param target_file_path: pathlib.Path object that we are going to count the empty rows of
    :return: count of empty rows in file
    """
    message = (
        f'In the count empty rows using awk function for {target_file_path}\n')
    log_info(message)
    awk_template = ("awk '!NF {sum += 1} END {print sum}' " +
        f'{target_file_path}')
    command = awk_template
    result = subprocess.run(command, shell=True, capture_output=True, text=True
        )
    message = (
        f'County empty rows in file using awk function for {target_file_path} has a result of {result.stdout}'
        )
    if result.stderr is None:
        error_code = 'None'
    else:
        error_code = result.stderr
    message = (
        f'Ran awk on {target_file_path}, result is {result.stdout}, error code is {error_code}'
        )
    subprocess_command_output = str(result.stdout)
    log_info(subprocess_command_output)
    if result.returncode == 0:
        if len(subprocess_command_output
            ) < 1 or subprocess_command_output == '\n':
            message = (
                f'The empty rows awk command returned no output {subprocess_command_output}, setting empty rows to 0'
                )
            log_info(message)
            empty_rows_count = 0
        else:
            message = (
                f'The empty rows awk command returned {subprocess_command_output}'
                )
            log_info(message)
            empty_rows_count = int(subprocess_command_output)
        message = (
            f'SUCCESS: Found {empty_rows_count} duplicate rows in file {target_file_path}, returning to memory'
            )
        log_info(message=message)
        return empty_rows_count
    else:
        empty_rows_count = False
        message = (
            f'There was an error counting empty rows in {target_file_path}: {result.stderr}'
            )
        log_error(message)
        return empty_rows_count


def remove_empty_rows_in_file_using_sed(target_file_path: pathlib.Path,
    fixed_file_path: pathlib.Path=None):
    """
    :param target_file_path: pathlib.Path object that we are going to remove the empty rows of
    :param target_file_path: pathlib.Path object to path for saved fixed file
    :return:
    """
    sed_template = f"sed '/^$/d' {target_file_path}"
    message = (
        f'In the remove empty rows using sed function for {target_file_path}\n'
        )
    message += f"""Received args target_file_path is {target_file_path}
, fixed_file_path is {fixed_file_path}"""
    log_info(message)
    if fixed_file_path is None:
        message = (
            f'No path was set for output for {target_file_path}, so this will remain StringIO'
            )
        log_info(message)
        output_file = io.StringIO()
    command = sed_template
    result = subprocess.run(command, shell=True, capture_output=True, text=True
        )
    subprocess_command_output = str(result.stdout)
    if result.stderr is None:
        error_code = 'None'
    else:
        error_code = result.stderr
    message = (
        f'Ran sed on {target_file_path}, result is {subprocess_command_output}, error code is {error_code}'
        )
    if result.returncode == 0:
        message = f'SUCCESS: Removed duplicate rows in file {target_file_path}'
        removed_rows_result = subprocess_command_output
        log_info(message)
        if fixed_file_path is None:
            message = (
                f'No path was set for output for {target_file_path}, so this will remain StringIO'
                )
            logger.info(message)
            output_file.write(removed_rows_result)
            return output_file
        else:
            message = (
                f'Output file path was set, returning path to file {fixed_file_path}'
                )
            log_info(message)
            delete_existing_file_and_replace_it_with_an_empty_file(
                target_file_path=fixed_file_path)
            fixed_file_path.write_text(removed_rows_result)
            message = (
                f'SUCCESS: Wrote rows removed data to {fixed_file_path}, about to return a path'
                )
            log_info(message)
            return fixed_file_path
    else:
        removed_rows_result = False
        message = (
            f'There was an error counting total rows in {target_file_path}: {result.stderr}'
            )
        log_error(message)
        return removed_rows_result


def write_data_to_a_new_empty_file(target_file_path: pathlib.Path, data: str
    ) ->pathlib.Path:
    """

    :param target_file_path: file path to write data to
    :param data: what to write
    :return: the path to the file
    """
    target_file_path = pathlib.Path(target_file_path)
    data = str(data)
    delete_existing_file_and_replace_it_with_an_empty_file(target_file_path
        =target_file_path)
    target_file_path.write_text(data)
    return target_file_path


def write_data_to_an_existing_file(target_file_path: pathlib.Path, data: str
    ) ->pathlib.Path:
    """

    :param target_file_path: file path to write data to
    :param data: what to write
    :return: the path to the file
    """
    target_file_path = pathlib.Path(target_file_path)
    data = str(f'\n{data}')
    with target_file_path.open('a') as file:
        file.write(data)
    return target_file_path


def check_for_file_type_in_directory(target_file_path: pathlib.Path,
    file_type: str) ->bool:
    """

    :param target_file_path:
    :param file_type:
    :return: bool
    """
    target_file_path = pathlib.Path(target_file_path)
    glob_string = f'*.{file_type}'
    found_files = list(target_file_path.glob(glob_string)
        ) if target_file_path.exists() else []
    found_files = [f for f in found_files if f.exists() and f.stat().
        st_size > 0]
    if len(found_files) > 0:
        message = f'Found {file_type} files: {found_files}'
        log_info(message)
        return True
    else:
        message = (
            f'No file was found for {file_type} in directory {target_file_path}'
            )
        log_info(message)
        return False
