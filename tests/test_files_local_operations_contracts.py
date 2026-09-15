import hashlib

import pytest

from siege_utilities import copy_file
from siege_utilities import file_exists
from siege_utilities import generate_sha256_hash_for_file
from siege_utilities import get_file_hash
from siege_utilities import move_file
from siege_utilities import verify_file_integrity


def test_file_exists_reports_existing_and_missing_paths(tmp_path):
    existing = tmp_path / "source.txt"
    existing.write_text("hello", encoding="utf-8")

    assert file_exists(existing) is True
    assert file_exists(tmp_path / "missing.txt") is False


def test_copy_file_preserves_source_and_requires_overwrite(
    tmp_path,
):
    source = tmp_path / "source.txt"
    destination = tmp_path / "nested" / "copy.txt"
    source.write_text("first", encoding="utf-8")

    copy_file(source, destination)

    assert source.read_text(encoding="utf-8") == "first"
    assert destination.read_text(encoding="utf-8") == "first"

    source.write_text("second", encoding="utf-8")
    with pytest.raises(FileExistsError, match="overwrite=False"):
        copy_file(source, destination)

    copy_file(source, destination, overwrite=True)
    assert source.read_text(encoding="utf-8") == "second"
    assert destination.read_text(encoding="utf-8") == "second"


def test_move_file_moves_source_and_requires_overwrite(
    tmp_path,
):
    source = tmp_path / "source.txt"
    destination = tmp_path / "nested" / "moved.txt"
    source.write_text("payload", encoding="utf-8")

    move_file(source, destination)

    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "payload"

    replacement = tmp_path / "replacement.txt"
    replacement.write_text("replacement", encoding="utf-8")
    with pytest.raises(FileExistsError, match="overwrite=False"):
        move_file(replacement, destination)

    move_file(replacement, destination, overwrite=True)
    assert not replacement.exists()
    assert destination.read_text(encoding="utf-8") == "replacement"


def test_hash_helpers_and_integrity_checks_use_requested_algorithm(tmp_path):
    path = tmp_path / "payload.bin"
    payload = b"siege-utilities\n"
    path.write_bytes(payload)
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    expected_md5 = hashlib.md5(payload).hexdigest()

    assert generate_sha256_hash_for_file(path) == expected_sha256
    assert get_file_hash(path) == expected_sha256
    assert get_file_hash(path, algorithm="md5") == expected_md5
    assert verify_file_integrity(path, expected_sha256) is True
    assert verify_file_integrity(path, expected_md5, algorithm="md5") is True
    assert verify_file_integrity(path, "0" * 64) is False
