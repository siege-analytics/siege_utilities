"""Tests for siege_utilities.files.operations — core file I/O functions."""

import json
from pathlib import Path

import pytest

from siege_utilities.files.operations import (
    copy_file,
    count_lines,
    delete_existing_file_and_replace_it_with_an_empty_file,
    ensure_directory_exists,
    file_exists,
    get_file_size,
    get_file_size_mb,
    list_directory,
    list_files_recursive,
    move_file,
    remove_tree,
    safe_file_read,
    safe_file_write,
    safe_json_read,
    safe_json_write,
    touch_file,
)


class TestFileExists:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hi")
        assert file_exists(f) is True

    def test_missing_file(self, tmp_path):
        assert file_exists(tmp_path / "nope.txt") is False

    def test_directory_returns_true(self, tmp_path):
        assert file_exists(tmp_path) is True


class TestTouchFile:
    def test_creates_file(self, tmp_path):
        target = tmp_path / "new.txt"
        assert touch_file(target) is True
        assert target.exists()

    def test_creates_parents(self, tmp_path):
        target = tmp_path / "a" / "b" / "c.txt"
        assert touch_file(target, create_parents=True) is True
        assert target.exists()

    def test_existing_file_updated(self, tmp_path):
        target = tmp_path / "old.txt"
        target.write_text("content")
        assert touch_file(target) is True


class TestCountLines:
    def test_counts_lines(self, tmp_path):
        f = tmp_path / "lines.txt"
        f.write_text("one\ntwo\nthree\n")
        assert count_lines(f) == 3

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        assert count_lines(f) == 0

    def test_missing_file_returns_none(self, tmp_path):
        assert count_lines(tmp_path / "missing.txt") is None


class TestCopyFile:
    def test_copies_content(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("data")
        dst = tmp_path / "dst.txt"
        assert copy_file(src, dst) is True
        assert dst.read_text() == "data"

    def test_no_overwrite_by_default(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("new")
        dst = tmp_path / "dst.txt"
        dst.write_text("old")
        assert copy_file(src, dst, overwrite=False) is False
        assert dst.read_text() == "old"

    def test_overwrite_when_requested(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("new")
        dst = tmp_path / "dst.txt"
        dst.write_text("old")
        assert copy_file(src, dst, overwrite=True) is True
        assert dst.read_text() == "new"


class TestMoveFile:
    def test_moves_file(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("data")
        dst = tmp_path / "dst.txt"
        assert move_file(src, dst) is True
        assert not src.exists()
        assert dst.read_text() == "data"

    def test_no_overwrite_by_default(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("new")
        dst = tmp_path / "dst.txt"
        dst.write_text("old")
        assert move_file(src, dst, overwrite=False) is False
        assert src.exists()


class TestGetFileSize:
    def test_returns_size(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("hello")
        size = get_file_size(f)
        assert size is not None
        assert size == 5

    def test_missing_file_returns_none(self, tmp_path):
        assert get_file_size(tmp_path / "missing.txt") is None


class TestGetFileSizeMb:
    def test_returns_megabytes(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"\x00" * 1048576)
        mb = get_file_size_mb(f)
        assert abs(mb - 1.0) < 0.01


class TestListDirectory:
    def test_lists_files_and_dirs(self, tmp_path):
        (tmp_path / "file.txt").touch()
        (tmp_path / "subdir").mkdir()
        result = list_directory(tmp_path)
        assert result is not None
        names = {p.name for p in result}
        assert "file.txt" in names
        assert "subdir" in names

    def test_pattern_filter(self, tmp_path):
        (tmp_path / "a.py").touch()
        (tmp_path / "b.txt").touch()
        result = list_directory(tmp_path, pattern="*.py")
        assert result is not None
        assert len(result) == 1
        assert result[0].name == "a.py"


class TestListFilesRecursive:
    def test_finds_nested_files(self, tmp_path):
        (tmp_path / "a.py").touch()
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.py").touch()
        result = list_files_recursive(tmp_path, pattern="*.py")
        assert len(result) == 2


class TestRemoveTree:
    def test_removes_directory(self, tmp_path):
        target = tmp_path / "to_delete"
        target.mkdir()
        (target / "file.txt").write_text("data")
        assert remove_tree(target) is True
        assert not target.exists()

    def test_missing_path_returns_false(self, tmp_path):
        assert remove_tree(tmp_path / "nope") is False


class TestDeleteAndReplace:
    def test_replaces_with_empty(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("content")
        assert delete_existing_file_and_replace_it_with_an_empty_file(f) is True
        assert f.exists()
        assert f.read_text() == ""


class TestEnsureDirectoryExists:
    def test_creates_directory(self, tmp_path):
        target = tmp_path / "new_dir"
        result = ensure_directory_exists(target)
        assert result == target
        assert target.is_dir()

    def test_existing_directory_ok(self, tmp_path):
        result = ensure_directory_exists(tmp_path)
        assert result == tmp_path


class TestSafeFileReadWrite:
    def test_roundtrip(self, tmp_path):
        f = tmp_path / "safe.txt"
        assert safe_file_write(f, "hello world") is True
        assert safe_file_read(f) == "hello world"

    def test_read_missing_returns_default(self, tmp_path):
        assert safe_file_read(tmp_path / "nope.txt", default="fallback") == "fallback"

    def test_write_creates_parents(self, tmp_path):
        f = tmp_path / "a" / "b" / "file.txt"
        assert safe_file_write(f, "nested") is True
        assert f.read_text() == "nested"


class TestSafeJsonReadWrite:
    def test_roundtrip(self, tmp_path):
        f = tmp_path / "data.json"
        data = {"key": "value", "list": [1, 2, 3]}
        assert safe_json_write(f, data) is True
        result = safe_json_read(f)
        assert result == data

    def test_read_missing_returns_default(self, tmp_path):
        assert safe_json_read(tmp_path / "nope.json", default={}) == {}
