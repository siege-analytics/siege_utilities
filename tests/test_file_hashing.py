"""Tests for siege_utilities.files.hashing — file hash functions."""
import hashlib
import os
import pytest

from siege_utilities.files.hashing import (
    generate_sha256_hash_for_file,
    get_file_hash,
    calculate_file_hash,
    get_quick_file_signature,
    verify_file_integrity,
)


@pytest.fixture
def sample_file(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("Hello, World! This is test content.")
    return f


@pytest.fixture
def large_file(tmp_path):
    f = tmp_path / "large.bin"
    # >1MB to trigger quick signature partial-hash path
    f.write_bytes(os.urandom(2 * 1024 * 1024))
    return f


class TestGenerateSha256:
    def test_basic(self, sample_file):
        result = generate_sha256_hash_for_file(str(sample_file))
        assert result is not None
        assert len(result) == 64  # SHA256 hex digest length

    def test_matches_hashlib(self, sample_file):
        expected = hashlib.sha256(sample_file.read_bytes()).hexdigest()
        assert generate_sha256_hash_for_file(str(sample_file)) == expected

    def test_nonexistent_returns_none(self):
        result = generate_sha256_hash_for_file("/tmp/nonexistent_file_abc123.txt")
        assert result is None

    def test_path_object(self, sample_file):
        result = generate_sha256_hash_for_file(sample_file)
        assert result is not None


class TestGetFileHash:
    def test_sha256(self, sample_file):
        result = get_file_hash(str(sample_file), "sha256")
        expected = hashlib.sha256(sample_file.read_bytes()).hexdigest()
        assert result == expected

    def test_md5(self, sample_file):
        result = get_file_hash(str(sample_file), "md5")
        expected = hashlib.md5(sample_file.read_bytes()).hexdigest()
        assert result == expected

    def test_sha1(self, sample_file):
        result = get_file_hash(str(sample_file), "sha1")
        expected = hashlib.sha1(sample_file.read_bytes()).hexdigest()
        assert result == expected

    def test_default_algorithm(self, sample_file):
        result = get_file_hash(str(sample_file))
        expected = hashlib.sha256(sample_file.read_bytes()).hexdigest()
        assert result == expected

    def test_nonexistent_returns_none(self):
        assert get_file_hash("/tmp/no_such_file_xyz.txt") is None


class TestCalculateFileHash:
    def test_alias(self, sample_file):
        assert calculate_file_hash(str(sample_file)) == get_file_hash(str(sample_file), "sha256")


class TestGetQuickFileSignature:
    def test_small_file(self, sample_file):
        sig = get_quick_file_signature(str(sample_file))
        assert sig is not None
        assert sig != "missing"
        assert sig != "error"

    def test_missing_file(self):
        sig = get_quick_file_signature("/tmp/no_such_file_xyz.txt")
        assert sig == "missing"

    def test_large_file_partial_hash(self, large_file):
        sig = get_quick_file_signature(str(large_file))
        assert sig is not None
        assert len(sig) == 64  # SHA256 hex digest

    def test_deterministic(self, sample_file):
        sig1 = get_quick_file_signature(str(sample_file))
        sig2 = get_quick_file_signature(str(sample_file))
        assert sig1 == sig2


class TestVerifyFileIntegrity:
    def test_valid_hash(self, sample_file):
        h = get_file_hash(str(sample_file), "sha256")
        assert verify_file_integrity(str(sample_file), h) is True

    def test_wrong_hash(self, sample_file):
        assert verify_file_integrity(str(sample_file), "0" * 64) is False

    def test_case_insensitive(self, sample_file):
        h = get_file_hash(str(sample_file), "sha256")
        assert verify_file_integrity(str(sample_file), h.upper()) is True

    def test_nonexistent_file(self):
        assert verify_file_integrity("/tmp/no_file.txt", "abc") is False

    def test_md5(self, sample_file):
        h = get_file_hash(str(sample_file), "md5")
        assert verify_file_integrity(str(sample_file), h, "md5") is True
