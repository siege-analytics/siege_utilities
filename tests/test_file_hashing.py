# ================================================================
# FILE: test_file_hashing.py
# ================================================================
"""
Tests for siege_utilities.files.hashing module.
These tests will expose issues with file hashing functions.
"""
import pytest
import hashlib
import pathlib
import siege_utilities


class TestHashingFunctions:
    """Test file hashing functionality and expose bugs."""

    def test_generate_sha256_hash_for_file_valid(self, sample_file):
        """Test SHA256 hash generation with valid file."""
        hash_result = siege_utilities.generate_sha256_hash_for_file(sample_file)

        assert hash_result is not None
        assert len(hash_result) == 64  # SHA256 hex length
        assert all(c in '0123456789abcdef' for c in hash_result.lower())

        # Verify it's actually the correct hash
        with open(sample_file, 'rb') as f:
            expected_hash = hashlib.sha256(f.read()).hexdigest()
        assert hash_result == expected_hash

    def test_generate_sha256_hash_nonexistent_file(self):
        """Test SHA256 hash with nonexistent file."""
        result = siege_utilities.generate_sha256_hash_for_file("/nonexistent/file.txt")
        assert result is None

    def test_get_file_hash_algorithms(self, sample_file):
        """Test different hash algorithms."""
        sha256_hash = siege_utilities.get_file_hash(sample_file, 'sha256')
        md5_hash = siege_utilities.get_file_hash(sample_file, 'md5')
        sha1_hash = siege_utilities.get_file_hash(sample_file, 'sha1')

        assert sha256_hash is not None and len(sha256_hash) == 64
        assert md5_hash is not None and len(md5_hash) == 32
        assert sha1_hash is not None and len(sha1_hash) == 40

    def test_get_file_hash_invalid_algorithm(self, sample_file):
        """Test get_file_hash with invalid algorithm."""
        result = siege_utilities.get_file_hash(sample_file, 'invalid_algo')
        assert result is None

    def test_verify_file_integrity(self, sample_file):
        """Test file integrity verification."""
        actual_hash = siege_utilities.get_file_hash(sample_file, 'sha256')

        # Test with correct hash
        assert siege_utilities.verify_file_integrity(sample_file, actual_hash, 'sha256') == True

        # Test with incorrect hash
        wrong_hash = 'a' * 64
        assert siege_utilities.verify_file_integrity(sample_file, wrong_hash, 'sha256') == False
