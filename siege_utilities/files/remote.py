import pathlib
import requests
import logging
import tqdm
logger = logging.getLogger(__name__)


def download_file(url, local_filename):
    """
    Download a file from a URL to a local file with progress bar

    Args:
        url: The URL to download from
        local_filename: The local path where the file should be saved

    Returns:
        The local filename if successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    try:
        logger.info(f'Attempting to download {url} to {local_filename}')
        with requests.get(url, stream=True, allow_redirects=True) as r:
            if r.ok:
                total_size = int(r.headers.get('content-length', 0))
                logger.info(f'Download started, file size: {total_size} bytes')
                initial_pos = 0
                with open(local_filename, 'wb') as f:
                    with tqdm(total=total_size, unit_scale=True, desc=
                        local_filename, initial=initial_pos, ascii=True) as pbar:
                        for chunk in r.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                logger.info(
                    f'Successfully downloaded {url} to {local_filename}')
                return local_filename
            else:
                logger.error(
                    f'Failed to download {url}: HTTP status {r.status_code}')
                return False
    except Exception as e:
        logger.error(f'Exception during download of {url}: {e}')
        return False


def generate_local_path_from_url(url: str, directory_path: pathlib.Path,
    as_string: bool=True):
    """""\"
Perform file operations: generate local path from url.

Part of Siege Utilities File Operations module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.generate_local_path_from_url()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    try:
        remote_file_name = url.split('/')[-1]
        directory_path = pathlib.Path(directory_path)
        new_path = directory_path / remote_file_name
        if as_string is True:
            new_path = str(new_path)
        message = (
            f'Successfully generated path {new_path}, as_string={as_string}')
        log_info(message=message)
        return new_path
    except Exception as e:
        message = f'Exception while generating local path: {e}'
        log_error(message=message)
        return False
