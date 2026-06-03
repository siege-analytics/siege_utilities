"""Tests for siege_utilities.files.operations — file manipulation utilities."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from siege_utilities.files.operations import (
    atomic_write_path,
    atomic_write_shapefile,
    remove_tree,
    file_exists,
    touch_file,
    count_lines,
    copy_file,
    move_file,
    get_file_size,
    list_directory,
    run_command,
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
        remove_tree(str(f))
        assert not f.exists()

    def test_remove_directory(self, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        (d / "file.txt").write_text("data")
        remove_tree(str(d))
        assert not d.exists()

    def test_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            remove_tree(str(tmp_path / "nope"))


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
        touch_file(str(f))
        assert f.exists()

    def test_create_with_parents(self, tmp_path):
        f = tmp_path / "a" / "b" / "c.txt"
        touch_file(str(f))
        assert f.exists()

    def test_existing_file(self, tmp_path):
        f = tmp_path / "existing.txt"
        f.write_text("data")
        touch_file(str(f))
        assert f.exists()


class TestCountLines:
    def test_basic(self, tmp_path):
        f = tmp_path / "lines.txt"
        f.write_text("line1\nline2\nline3\n")
        assert count_lines(str(f)) == 3

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        assert count_lines(str(f)) == 0

    def test_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            count_lines(str(tmp_path / "nope.txt"))


class TestCopyFile:
    def test_copy(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("content")
        dst = tmp_path / "dst.txt"
        copy_file(str(src), str(dst))
        assert dst.read_text() == "content"

    def test_copy_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            copy_file(str(tmp_path / "nope.txt"), str(tmp_path / "dst.txt"))

    def test_copy_no_overwrite_raises(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("content")
        dst = tmp_path / "dst.txt"
        dst.write_text("existing")
        with pytest.raises(FileExistsError):
            copy_file(str(src), str(dst))


class TestMoveFile:
    def test_move(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("content")
        dst = tmp_path / "dst.txt"
        move_file(str(src), str(dst))
        assert not src.exists()
        assert dst.read_text() == "content"

    def test_move_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            move_file(str(tmp_path / "nope.txt"), str(tmp_path / "dst.txt"))

    def test_move_no_overwrite_raises(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("content")
        dst = tmp_path / "dst.txt"
        dst.write_text("existing")
        with pytest.raises(FileExistsError):
            move_file(str(src), str(dst))


class TestGetFileSize:
    def test_size(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        size = get_file_size(str(f))
        assert size == 5

    def test_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            get_file_size(str(tmp_path / "nope.txt"))


class TestListDirectory:
    def test_list(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        result = list_directory(str(tmp_path))
        assert len(result) >= 2

    def test_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            list_directory(str(tmp_path / "nope"))


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


class TestAtomicWritePath:
    def test_successful_write_replaces_target(self, tmp_path):
        target = tmp_path / "output.csv"
        target.write_text("old data")
        with atomic_write_path(target) as tmp:
            tmp.write_text("new data")
        assert target.read_text() == "new data"

    def test_failed_write_leaves_target_unchanged(self, tmp_path):
        target = tmp_path / "output.csv"
        target.write_text("original")
        with pytest.raises(ValueError):
            with atomic_write_path(target) as tmp:
                tmp.write_text("partial")
                raise ValueError("simulated failure")
        assert target.read_text() == "original"

    def test_failed_write_cleans_up_temp(self, tmp_path):
        target = tmp_path / "output.csv"
        captured_tmp = None
        with pytest.raises(RuntimeError):
            with atomic_write_path(target) as tmp:
                captured_tmp = tmp
                tmp.write_text("data")
                raise RuntimeError("boom")
        assert not captured_tmp.exists()

    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "file.txt"
        with atomic_write_path(target) as tmp:
            tmp.write_text("nested")
        assert target.read_text() == "nested"

    def test_preserves_extension(self, tmp_path):
        target = tmp_path / "data.parquet"
        with atomic_write_path(target) as tmp:
            assert tmp.suffix == ".parquet"
            tmp.write_text("fake parquet")


class TestRunCommand:
    """Tests for run_command — security validation, allow-list, and execution."""

    def test_allowed_command_succeeds(self):
        result = run_command("echo hello")
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_allowed_command_as_list(self):
        result = run_command(["echo", "hello world"])
        assert result.returncode == 0
        assert "hello world" in result.stdout

    def test_disallowed_command_raises(self):
        from siege_utilities.files.shell import SecurityError
        with pytest.raises(SecurityError):
            run_command("python --version")

    def test_custom_allow_list(self):
        result = run_command("true", allow_list={"true"})
        assert result.returncode == 0

    def test_unsafe_bypasses_allow_list(self):
        result = run_command("true", unsafe=True)
        assert result.returncode == 0

    def test_unsafe_rejects_shell_metacharacters_in_string(self):
        with pytest.raises(ValueError, match="shell metacharacters"):
            run_command("echo hello | cat", unsafe=True)

    def test_unsafe_list_form_allows_non_allowed_command(self):
        result = run_command(["true"], unsafe=True)
        assert result.returncode == 0

    def test_nonzero_exit_returns_completed_process(self):
        result = run_command("ls /nonexistent_path_xyz_abc")
        assert result.returncode != 0
        assert isinstance(result, subprocess.CompletedProcess)

    def test_cwd_is_respected(self, tmp_path):
        result = run_command("pwd", cwd=str(tmp_path))
        assert str(tmp_path) in result.stdout

    def test_timeout_raises(self):
        with pytest.raises(subprocess.TimeoutExpired):
            run_command(["sleep", "10"], allow_list={"sleep"}, timeout=1)

    def test_dangerous_chars_blocked(self):
        from siege_utilities.files.shell import SecurityError
        with pytest.raises(SecurityError):
            run_command("echo hello; rm -rf /")

    def test_path_traversal_blocked(self):
        from siege_utilities.files.shell import SecurityError
        with pytest.raises(SecurityError):
            run_command("cat ../../some/file")


class TestAtomicWriteShapefile:
    """Tests for atomic_write_shapefile — atomic GeoDataFrame→Shapefile."""

    def test_writes_shapefile_and_sidecars(self, tmp_path):
        target = tmp_path / "output.shp"
        mock_gdf = MagicMock()

        def fake_to_file(path, driver, **kwargs):
            p = Path(path)
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                (p.parent / (p.stem + ext)).write_text(f"fake {ext}")

        mock_gdf.to_file = fake_to_file
        atomic_write_shapefile(mock_gdf, target)
        for ext in (".shp", ".shx", ".dbf", ".prj"):
            assert (tmp_path / f"output{ext}").exists()

    def test_cleans_up_on_failure(self, tmp_path):
        target = tmp_path / "output.shp"
        mock_gdf = MagicMock()
        mock_gdf.to_file.side_effect = RuntimeError("write failed")
        with pytest.raises(RuntimeError):
            atomic_write_shapefile(mock_gdf, target)
        assert not target.exists()
        assert list(tmp_path.glob("atomic_shp_*")) == []

    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "a" / "b" / "output.shp"
        mock_gdf = MagicMock()

        def fake_to_file(path, driver, **kwargs):
            p = Path(path)
            for ext in (".shp", ".shx", ".dbf"):
                (p.parent / (p.stem + ext)).write_text(f"fake {ext}")

        mock_gdf.to_file = fake_to_file
        atomic_write_shapefile(mock_gdf, target)
        assert target.exists()
