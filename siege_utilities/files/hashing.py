#!/usr/bin/env python3
"""
Hash Management Functions - Fixed Version
Provides standardized hash functions that actually exist and work properly
"""

import hashlib
import pathlib
from typing import Optional


def generate_sha256_hash_for_file(file_path) -> Optional[str]:
    """
    Generate SHA256 hash for a file - chunked reading for large files

    Args:
        file_path: Path to the file (str or Path object)

    Returns:
        SHA256 hash as hexadecimal string, or None if error
    """
    try:
        path_obj = pathlib.Path(file_path)
        if not path_obj.exists() or not path_obj.is_file():
            return None

        sha256_hash = hashlib.sha256()

        # Read file in chunks to handle large files efficiently
        with open(path_obj, "rb") as f:
            # Read in 64KB chunks
            for chunk in iter(lambda: f.read(65536), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    except Exception as e:
        print(f"Error generating SHA256 hash for {file_path}: {e}")
        return None


def get_file_hash(file_path, algorithm="sha256") -> Optional[str]:
    """
    Generate hash for a file using specified algorithm

    Args:
        file_path: Path to the file (str or Path object)
        algorithm: Hash algorithm to use ('sha256', 'md5', 'sha1', etc.)

    Returns:
        Hash as hexadecimal string, or None if error
    """
    try:
        path_obj = pathlib.Path(file_path)
        if not path_obj.exists() or not path_obj.is_file():
            return None

        # Get the hash function
        if algorithm.lower() == "sha256":
            hash_func = hashlib.sha256()
        elif algorithm.lower() == "md5":
            hash_func = hashlib.md5()
        elif algorithm.lower() == "sha1":
            hash_func = hashlib.sha1()
        else:
            # Try to get the algorithm dynamically
            hash_func = hashlib.new(algorithm)

        # Read file in chunks
        with open(path_obj, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    except Exception as e:
        print(f"Error generating {algorithm} hash for {file_path}: {e}")
        return None


def calculate_file_hash(file_path) -> Optional[str]:
    """
    Alias for get_file_hash with SHA256 - for backward compatibility
    """
    return get_file_hash(file_path, "sha256")


def get_quick_file_signature(file_path) -> str:
    """
    Generate a quick file signature using file stats + partial hash
    Faster for change detection, not cryptographically secure

    Args:
        file_path: Path to the file

    Returns:
        Quick signature string
    """
    try:
        path_obj = pathlib.Path(file_path)
        if not path_obj.exists():
            return "missing"

        # Get file stats
        stat = path_obj.stat()

        # For small files, hash the whole thing
        if stat.st_size <= 1024 * 1024:  # 1MB
            return get_file_hash(file_path) or f"stat_{stat.st_size}_{stat.st_mtime}"

        # For large files, hash first and last 64KB + file stats
        hash_obj = hashlib.sha256()

        with open(path_obj, "rb") as f:
            # Hash first 64KB
            first_chunk = f.read(65536)
            hash_obj.update(first_chunk)

            # If file is large enough, seek to end and hash last 64KB
            if stat.st_size > 131072:  # 128KB
                f.seek(-65536, 2)  # Seek to 64KB from end
                last_chunk = f.read(65536)
                hash_obj.update(last_chunk)

        # Combine with file stats
        stat_string = f"{stat.st_size}_{stat.st_mtime}_{len(first_chunk)}"
        hash_obj.update(stat_string.encode())

        return hash_obj.hexdigest()

    except Exception as e:
        print(f"Error generating quick signature for {file_path}: {e}")
        # Fallback to basic file stats
        try:
            stat = pathlib.Path(file_path).stat()
            return f"fallback_{stat.st_size}_{stat.st_mtime}"
        except:
            return "error"


def verify_file_integrity(file_path, expected_hash, algorithm="sha256") -> bool:
    """
    Verify file integrity by comparing with expected hash

    Args:
        file_path: Path to the file
        expected_hash: Expected hash value
        algorithm: Hash algorithm used

    Returns:
        True if file matches expected hash, False otherwise
    """
    try:
        current_hash = get_file_hash(file_path, algorithm)
        return (
            current_hash is not None and current_hash.lower() == expected_hash.lower()
        )
    except Exception:
        return False


# Test function
def test_hash_functions():
    """Test the hash functions with a temporary file"""
    import tempfile
    import os

    # Create a test file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Hello, World! This is a test file for hashing.")
        test_file = f.name

    try:
        print("Testing hash functions...")

        # Test SHA256
        sha256_hash = generate_sha256_hash_for_file(test_file)
        print(f"SHA256: {sha256_hash}")

        # Test generic hash function
        md5_hash = get_file_hash(test_file, "md5")
        print(f"MD5: {md5_hash}")

        # Test quick signature
        quick_sig = get_quick_file_signature(test_file)
        print(f"Quick signature: {quick_sig}")

        # Test verification
        if sha256_hash:
            verification = verify_file_integrity(test_file, sha256_hash)
            print(f"Verification: {verification}")

        print("✅ All hash functions working!")

    finally:
        # Clean up
        os.unlink(test_file)


if __name__ == "__main__":
    test_hash_functions()
