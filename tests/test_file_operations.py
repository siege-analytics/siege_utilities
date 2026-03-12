"""Tests for siege_utilities.files.operations — file manipulation utilities."""
import json
import pytest
from pathlib import Path

from siege_utilities.files.operations import (
    remove_tree,
    file_exists,
    touch_file,
    count_lines,
    copy_file,
    move_file,
    get_file_size,
    list_directory,
    ensure_directory_exists,
    safe_file_write,
    safe_file_read,
    safe_json_write,
    safe_json_read,
    get_file_size_mb,
    list_files_recursive,
    delete_existing_file_and_replace_it_with_an_empty_file,
)


class TestRemoveTree:
    def test_remove_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert remove_tree(str(f)) is True
        assert not f.exists()

    def test_remove_directory(self, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        (d / "file.txt").write_text("data")
        assert remove_tree(str(d)) is True
        assert not d.exists()

    def test_nonexistent(self, tmp_path):
        assert remove_tree(str(tmp_path / "nope")) is False


class TestFileExists:
    def test_exists(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert file_exists(str(f)) is True

    def test_not_exists(self, tmp_path):
        assert file_exists(str(tmp_path / "nope.txt")) is False


class TestTouchFile:
    def test_create(self, tmp_path):
        f = tmp_path / "new.txt"
        assert touch_file(str(f)) is True
        assert f.exists()

    def test_create_with_parents(self, tmp_path):
        f = tmp_path / "a" / "b" / "c.txt"
        assert touch_file(str(f)) is True
        assert f.exists()

    def test_existing_file(self, tmp_path):
        f = tmp_path / "existing.txt"
        f.write_text("data")
        assert touch_file(str(f)) is True


class TestCountLines:
    def test_basic(self, tmp_path):
        f = tmp_path / "lines.txt"
        f.write_text("line1\nline2\nline3\n")
        assert count_lines(str(f)) == 3

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        assert count_lines(str(f)) == 0

    def test_nonexistent(self, tmp_path):
        result = count_lines(str(tmp_path / "nope.txt"))
        assert result == 0 or result is None


class TestCopyFile:
    def test_copy(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("content")
        dst = tmp_path / "dst.txt"
        assert copy_file(str(src), str(dst)) is True
        assert dst.read_text() == "content"


class TestMoveFile:
    def test_move(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("content")
        dst = tmp_path / "dst.txt"
        assert move_file(str(src), str(dst)) is True
        assert not src.exists()
        assert dst.read_text() == "content"


class TestGetFileSize:
    def test_size(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        size = get_file_size(str(f))
        assert size == 5


class TestListDirectory:
    def test_list(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        result = list_directory(str(tmp_path))
        assert len(result) >= 2


class TestEnsureDirectoryExists:
    def test_create(self, tmp_path):
        d = tmp_path / "new_dir"
        ensure_directory_exists(str(d))
        assert d.is_dir()

    def test_existing(self, tmp_path):
        ensure_directory_exists(str(tmp_path))
        assert tmp_path.is_dir()


class TestSafeFileWriteRead:
    def test_write_and_read(self, tmp_path):
        f = tmp_path / "safe.txt"
        safe_file_write(str(f), "hello world")
        assert safe_file_read(str(f)) == "hello world"

    def test_read_nonexistent(self, tmp_path):
        result = safe_file_read(str(tmp_path / "nope.txt"))
        assert result is None or result == ""


class TestSafeJsonWriteRead:
    def test_round_trip(self, tmp_path):
        f = tmp_path / "data.json"
        data = {"key": "value", "num": 42, "list": [1, 2, 3]}
        safe_json_write(str(f), data)
        result = safe_json_read(str(f))
        assert result == data

    def test_read_nonexistent(self, tmp_path):
        result = safe_json_read(str(tmp_path / "nope.json"))
        assert result is None or result == {}


class TestGetFileSizeMb:
    def test_size(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"x" * 1024 * 1024)
        size = get_file_size_mb(str(f))
        assert abs(size - 1.0) < 0.01


class TestListFilesRecursive:
    def test_recursive(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("b")
        result = list_files_recursive(str(tmp_path))
        assert len(result) >= 2


class TestDeleteAndReplace:
    def test_replace_with_empty(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("some content")
        delete_existing_file_and_replace_it_with_an_empty_file(str(f))
        assert f.exists()
        assert f.read_text() == ""
