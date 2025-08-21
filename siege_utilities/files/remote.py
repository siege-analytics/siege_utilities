"""
Modern remote file operations for siege_utilities.
Provides clean, type-safe file download utilities.
"""

import pathlib
import requests
import logging
from pathlib import Path
from typing import Union, Optional
from urllib.parse import urlparse
import tqdm

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]

def download_file(url: str, local_filename: FilePath, 
                 chunk_size: int = 8192,
                 timeout: int = 30,
                 verify_ssl: bool = True) -> Union[str, bool]:
    """
    Download a file from a URL to a local file with progress bar.
    
    Args:
        url: The URL to download from
        local_filename: The local path where the file should be saved
        chunk_size: Size of chunks to download at once
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        
    Returns:
        The local filename if successful, False otherwise
        
    Example:
        >>> result = download_file("https://example.com/file.zip", "downloads/file.zip")
        >>> if result:
        ...     print(f"Downloaded to {result}")
    """
    try:
        log.info(f'Downloading {url} to {local_filename}')
        
        # Ensure local filename is a Path object
        local_path = Path(local_filename)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Make the request with streaming
        with requests.get(url, stream=True, allow_redirects=True, 
                         timeout=timeout, verify=verify_ssl) as response:
            
            if not response.ok:
                log.error(f'Download failed: HTTP {response.status_code} - {response.reason}')
                return False
            
            # Get total size for progress bar
            total_size = int(response.headers.get('content-length', 0))
            
            if total_size > 0:
                log.info(f'Download started, file size: {total_size} bytes')
            else:
                log.info('Download started, file size unknown')
            
            # Download with progress bar
            with open(local_path, 'wb') as file:
                with tqdm.tqdm(
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
            
            log.info(f'Successfully downloaded {url} to {local_path}')
            return str(local_path)
            
    except requests.exceptions.SSLError as e:
        log.warning(f'SSL verification failed for {url}, retrying without verification: {e}')
        # Retry without SSL verification
        try:
            with requests.get(url, stream=True, allow_redirects=True, 
                           timeout=timeout, verify=False) as response:
                
                if not response.ok:
                    log.error(f'Download failed without SSL: HTTP {response.status_code} - {response.reason}')
                    return False
                
                # Get total size for progress bar
                total_size = int(response.headers.get('content-length', 0))
                
                if total_size > 0:
                    log.info(f'Download started without SSL, file size: {total_size} bytes')
                else:
                    log.info('Download started without SSL, file size unknown')
                
                # Download with progress bar
                with open(local_path, 'wb') as file:
                    with tqdm.tqdm(
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        desc=f"{local_path.name} (no SSL)",
                        ascii=True
                    ) as progress_bar:
                        
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                file.write(chunk)
                                progress_bar.update(len(chunk))
                
                log.info(f'Successfully downloaded {url} to {local_path} without SSL verification')
                return str(local_path)
                
        except Exception as retry_error:
            log.error(f'Download failed even without SSL verification: {retry_error}')
            return False
            
    except requests.exceptions.Timeout:
        log.error(f'Download timed out for {url}')
        return False
    except requests.exceptions.RequestException as e:
        log.error(f'Request error downloading {url}: {e}')
        return False
    except Exception as e:
        log.error(f'Unexpected error downloading {url}: {e}')
        return False

def generate_local_path_from_url(url: str, directory_path: FilePath,
                                as_string: bool = True) -> Union[Path, str, bool]:
    """
    Generate a local file path from a URL.
    
    Args:
        url: URL to extract filename from
        directory_path: Directory where the file should be saved
        as_string: Whether to return the result as a string
        
    Returns:
        Path object, string, or False if failed
        
    Example:
        >>> path = generate_local_path_from_url("https://example.com/file.zip", "downloads")
        >>> print(f"Local path: {path}")
    """
    try:
        # Parse URL to get filename
        parsed_url = urlparse(url)
        remote_filename = parsed_url.path.split('/')[-1]
        
        if not remote_filename:
            log.warning(f'Could not extract filename from URL: {url}')
            return False
        
        # Ensure directory path is a Path object
        dir_path = Path(directory_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create full local path
        local_path = dir_path / remote_filename
        
        log.info(f'Generated local path: {local_path}')
        
        if as_string:
            return str(local_path)
        else:
            return local_path
            
    except Exception as e:
        log.error(f'Error generating local path from {url}: {e}')
        return False

def download_file_with_retry(url: str, local_filename: FilePath,
                            max_retries: int = 3,
                            retry_delay: int = 5,
                            **kwargs) -> Union[str, bool]:
    """
    Download a file with automatic retry on failure.
    
    Args:
        url: The URL to download from
        local_filename: The local path where the file should be saved
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        **kwargs: Additional arguments passed to download_file
        
    Returns:
        The local filename if successful, False otherwise
        
    Example:
        >>> result = download_file_with_retry("https://example.com/file.zip", "file.zip")
        >>> if result:
        ...     print("Download succeeded after retries")
    """
    import time
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                log.info(f'Retry attempt {attempt}/{max_retries} for {url}')
                time.sleep(retry_delay)
            
            result = download_file(url, local_filename, **kwargs)
            if result:
                return result
                
        except Exception as e:
            log.warning(f'Download attempt {attempt + 1} failed: {e}')
    
    log.error(f'Download failed after {max_retries + 1} attempts for {url}')
    return False

def get_file_info(url: str, timeout: int = 10) -> Optional[dict]:
    """
    Get information about a remote file without downloading it.
    
    Args:
        url: URL to get information about
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with file information, or None if failed
        
    Example:
        >>> info = get_file_info("https://example.com/file.zip")
        >>> if info:
        ...     print(f"File size: {info['size']} bytes")
    """
    try:
        log.debug(f'Getting file info for {url}')
        
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        
        if not response.ok:
            log.warning(f'Failed to get file info: HTTP {response.status_code}')
            return None
        
        info = {
            'url': url,
            'size': int(response.headers.get('content-length', 0)),
            'content_type': response.headers.get('content-type', 'unknown'),
            'last_modified': response.headers.get('last-modified'),
            'etag': response.headers.get('etag')
        }
        
        log.debug(f'File info for {url}: {info}')
        return info
        
    except Exception as e:
        log.error(f'Error getting file info for {url}: {e}')
        return None

def is_downloadable(url: str, timeout: int = 10) -> bool:
    """
    Check if a URL points to a downloadable file.
    
    Args:
        url: URL to check
        timeout: Request timeout in seconds
        
    Returns:
        True if the URL points to a downloadable file
        
    Example:
        >>> if is_downloadable("https://example.com/file.zip"):
        ...     print("URL is downloadable")
    """
    try:
        info = get_file_info(url, timeout)
        if info and info['size'] > 0:
            return True
        
        # Try a GET request to see if we can access the content
        response = requests.get(url, stream=True, timeout=timeout)
        return response.ok
        
    except Exception:
        return False

__all__ = [
    'download_file',
    'generate_local_path_from_url',
    'download_file_with_retry',
    'get_file_info',
    'is_downloadable'
]
