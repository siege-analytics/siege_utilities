"""
Modern remote file operations for siege_utilities.
Provides clean, type-safe file download utilities.
"""

import logging
import os
import platform
from pathlib import Path
from typing import Union, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None
from urllib.parse import urlparse

try:
    import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None

try:
    from siege_utilities.files.validation import PathSecurityError
except ImportError:
    class PathSecurityError(Exception):
        """Stub for when validation module is unavailable."""

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]


def _safe_content_length(response) -> int:
    """Parse Content-Length header, returning 0 on missing or malformed values."""
    raw = response.headers.get('content-length')
    if raw is None:
        return 0
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 0

def _get_ssl_verify_path():
    """Get the appropriate SSL certificate verification path for the current platform."""
    # macOS system CA bundle path (works better than certifi for some sites)
    if platform.system() == 'Darwin' and os.path.exists('/etc/ssl/cert.pem'):
        return '/etc/ssl/cert.pem'
    
    # Try certifi bundle if available
    try:
        import certifi
        return certifi.where()
    except ImportError:
        pass
    
    # Default to True (use system default)
    return True

def _check_requests_dependency():
    """Check if requests is available and raise informative error if not."""
    if not REQUESTS_AVAILABLE:
        raise ImportError(
            "requests library is required for remote file operations. "
            "Install with: pip install requests"
        )

class _DummyProgressBar:
    """Dummy progress bar when tqdm is not available."""
    def __init__(self, *args, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def update(self, n=1):
        pass

def _get_progress_bar(*args, **kwargs):
    """Get progress bar, using tqdm if available, dummy otherwise."""
    if TQDM_AVAILABLE:
        return tqdm.tqdm(*args, **kwargs)
    else:
        return _DummyProgressBar(*args, **kwargs)

def download_file(url: str, local_filename: FilePath,
                 chunk_size: int = 8192,
                 timeout: int = 30,
                 verify_ssl: bool = True) -> str:
    """
    Download a file from a URL to a local file with progress bar.

    SECURITY: Validates local file path to prevent path traversal attacks.

    Args:
        url: The URL to download from
        local_filename: The local path where the file should be saved
        chunk_size: Size of chunks to download at once
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates

    Returns:
        The local filename as a string.

    Raises:
        PathSecurityError: If local path fails security validation.
        requests.exceptions.HTTPError: If the server returns a non-2xx status.
        requests.exceptions.Timeout: On request timeout.
        requests.exceptions.RequestException: On other network failures.
        OSError: On filesystem failure.
    """
    _check_requests_dependency()

    log.info(f'Downloading {url} to {local_filename}')

    try:
        from siege_utilities.files.validation import validate_safe_path, PathSecurityError
        local_path = validate_safe_path(local_filename, allow_absolute=True)
    except ImportError:
        local_path = Path(local_filename)

    local_path.parent.mkdir(parents=True, exist_ok=True)

    ssl_verify = _get_ssl_verify_path() if verify_ssl else False
    headers = {'User-Agent': 'siege_utilities/1.0 (Census/GIS data client)'}

    try:
        with requests.get(url, stream=True, allow_redirects=True,
                         timeout=timeout, verify=ssl_verify,
                         headers=headers) as response:
            response.raise_for_status()
            _download_response_to_file(response, local_path, chunk_size)
            log.info(f'Successfully downloaded {url} to {local_path}')
            return str(local_path)

    except requests.exceptions.SSLError as e:
        log.warning(f'SSL verification failed for {url}, retrying without verification: {e}')
        with requests.get(url, stream=True, allow_redirects=True,
                       timeout=timeout, verify=False,
                       headers=headers) as response:
            response.raise_for_status()
            _download_response_to_file(response, local_path, chunk_size)
            log.info(f'Successfully downloaded {url} to {local_path} without SSL verification')
            return str(local_path)


def _download_response_to_file(response, local_path: Path, chunk_size: int) -> None:
    """Write a streaming response to a local file with progress bar."""
    total_size = _safe_content_length(response)

    with open(local_path, 'wb') as file:
        with _get_progress_bar(
            total=total_size,
            unit='B',
            unit_scale=True,
            desc=local_path.name,
            ascii=True
        ) as progress_bar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)
                    progress_bar.update(len(chunk))

def generate_local_path_from_url(url: str, directory_path: FilePath,
                                as_string: bool = True) -> Union[Path, str]:
    """
    Generate a local file path from a URL.

    SECURITY: Validates directory path to prevent path traversal attacks.

    Args:
        url: URL to extract filename from
        directory_path: Directory where the file should be saved
        as_string: Whether to return the result as a string

    Returns:
        Path object or string.

    Raises:
        PathSecurityError: If directory path fails security validation.
        ValueError: If no filename can be extracted from the URL.
        OSError: On directory creation failure.
    """
    parsed_url = urlparse(url)
    remote_filename = parsed_url.path.split('/')[-1]

    if not remote_filename:
        raise ValueError(f'Could not extract filename from URL: {url}')

    try:
        from siege_utilities.files.validation import validate_directory_path, PathSecurityError
        dir_path = validate_directory_path(directory_path, must_exist=False)
    except ImportError:
        dir_path = Path(directory_path)

    dir_path.mkdir(parents=True, exist_ok=True)

    local_path = dir_path / remote_filename

    log.info(f'Generated local path: {local_path}')

    if as_string:
        return str(local_path)
    else:
        return local_path

def download_file_with_retry(url: str, local_filename: FilePath,
                            max_retries: int = 3,
                            retry_delay: int = 5,
                            **kwargs) -> str:
    """
    Download a file with automatic retry on failure.

    Args:
        url: The URL to download from
        local_filename: The local path where the file should be saved
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        **kwargs: Additional arguments passed to download_file

    Returns:
        The local filename as a string.

    Raises:
        The last exception from download_file after all retries are exhausted.
    """
    import time

    last_error: Optional[BaseException] = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                log.info(f'Retry attempt {attempt}/{max_retries} for {url}')
                time.sleep(retry_delay)

            return download_file(url, local_filename, **kwargs)

        except (OSError, requests.exceptions.RequestException) as e:
            last_error = e
            log.warning(f'Download attempt {attempt + 1} failed: {e}')

    raise last_error  # type: ignore[misc]

def get_file_info(url: str, timeout: int = 10) -> dict:
    """
    Get information about a remote file without downloading it.

    Args:
        url: URL to get information about
        timeout: Request timeout in seconds

    Returns:
        Dictionary with file information (url, size, content_type, last_modified, etag).

    Raises:
        requests.exceptions.HTTPError: If the server returns a non-2xx status.
        requests.exceptions.RequestException: On network failure.
    """
    _check_requests_dependency()
    log.debug(f'Getting file info for {url}')

    response = requests.head(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()

    info = {
        'url': url,
        'size': _safe_content_length(response),
        'content_type': response.headers.get('content-type', 'unknown'),
        'last_modified': response.headers.get('last-modified'),
        'etag': response.headers.get('etag')
    }

    log.debug(f'File info for {url}: {info}')
    return info

def is_downloadable(url: str, timeout: int = 10) -> bool:
    """
    Check if a URL points to a downloadable file.

    Args:
        url: URL to check
        timeout: Request timeout in seconds

    Returns:
        True if the URL points to a downloadable file (has content).

    Raises:
        requests.exceptions.RequestException: On network failure.
    """
    _check_requests_dependency()
    info = get_file_info(url, timeout)
    if info['size'] > 0:
        return True

    response = requests.get(url, stream=True, timeout=timeout)
    response.close()
    return response.ok

__all__ = [
    'download_file',
    'generate_local_path_from_url',
    'download_file_with_retry',
    'get_file_info',
    'is_downloadable'
]
