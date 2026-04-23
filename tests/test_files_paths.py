"""First tests for siege_utilities.files.paths (ELE-2419)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from siege_utilities.files.paths import (
    create_backup_path,
    ensure_path_exists,
    find_files_by_pattern,
    get_file_extension,
    get_file_name_without_extension,
    get_relative_path,
    is_hidden_file,
    normalize_path,
    unzip_file_to_directory,
)


class TestEnsurePathExists:
    def test_creates_missing_directory(self, tmp_path):
        target = tmp_path / "new" / "nested" / "dir"
        result = ensure_path_exists(target)
        assert result.exists()
        assert result.is_dir()
        assert (result / ".gitkeep").exists()

    def test_existing_directory_is_ok(self, tmp_path):
        result = ensure_path_exists(tmp_path)
        assert result == tmp_path.resolve() or result == tmp_path

    def test_returns_path_object(self, tmp_path):
        result = ensure_path_exists(tmp_path / "x")
        assert isinstance(result, Path)


class TestGetFileExtension:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("document.pdf", ".pdf"),
            ("archive.tar.gz", ".gz"),
            ("noext", ""),
            ("dir/file.txt", ".txt"),
        ],
    )
    def test_returns_suffix(self, name, expected):
        assert get_file_extension(name) == expected


class TestGetFileNameWithoutExtension:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("document.pdf", "document"),
            ("archive.tar.gz", "archive.tar"),
            ("noext", "noext"),
        ],
    )
    def test_returns_stem(self, name, expected):
        assert get_file_name_without_extension(name) == expected


class TestIsHiddenFile:
    @pytest.mark.parametrize(
        "name,expected",
        [
            (".hidden", True),
            (".config", True),
            (".config/ssh", False),  # only the last component matters
            ("visible", False),
            ("normal.txt", False),
        ],
    )
    def test_detects_leading_dot(self, name, expected):
        assert is_hidden_file(name) is expected


class TestGetRelativePath:
    def test_target_inside_base(self, tmp_path):
        base = tmp_path
        target = tmp_path / "sub" / "file.txt"
        target.parent.mkdir()
        target.touch()
        result = get_relative_path(base, target)
        assert result == Path("sub/file.txt")

    def test_target_outside_base_returns_none(self, tmp_path):
        base = tmp_path / "a"
        base.mkdir()
        other = tmp_path / "b"
        other.mkdir()
        assert get_relative_path(base, other) is None


class TestFindFilesByPattern:
    def test_non_recursive_matches_shallow(self, tmp_path):
        (tmp_path / "a.csv").touch()
        (tmp_path / "b.csv").touch()
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "c.csv").touch()

        result = find_files_by_pattern(tmp_path, "*.csv", recursive=False)
        names = sorted(f.name for f in result)
        assert names == ["a.csv", "b.csv"]

    def test_recursive_finds_nested(self, tmp_path):
        (tmp_path / "a.csv").touch()
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "c.csv").touch()

        result = find_files_by_pattern(tmp_path, "*.csv", recursive=True)
        assert len(result) == 2

    def test_missing_directory_returns_empty(self, tmp_path):
        # validation.validate_directory_path may raise on must_exist; fall
        # back behavior returns []
        result = find_files_by_pattern(tmp_path / "nope", "*", recursive=False)
        assert result == []

    def test_result_is_sorted(self, tmp_path):
        for name in ["c.txt", "a.txt", "b.txt"]:
            (tmp_path / name).touch()
        result = find_files_by_pattern(tmp_path, "*.txt")
        names = [p.name for p in result]
        assert names == sorted(names)


class TestCreateBackupPath:
    def test_default_suffix(self, tmp_path):
        original = tmp_path / "config.yaml"
        original.touch()
        backup = create_backup_path(original)
        assert backup.name == "config.backup.yaml"
        assert backup.parent == tmp_path

    def test_custom_suffix_and_dir(self, tmp_path):
        original = tmp_path / "config.yaml"
        original.touch()
        target_dir = tmp_path / "backups"
        backup = create_backup_path(original, backup_suffix=".bak", backup_dir=target_dir)
        assert backup.name == "config.bak.yaml"
        assert backup.parent == target_dir
        assert target_dir.exists()


class TestNormalizePath:
    def test_resolves_user_home(self):
        result = normalize_path("~")
        assert result.is_absolute()
        assert str(result) == str(Path.home().resolve())

    def test_resolves_relative(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = normalize_path("./sub/../file.txt")
        assert result == (tmp_path / "file.txt").resolve()


class TestUnzipFileToDirectory:
    def test_extracts_archive(self, tmp_path):
        archive = tmp_path / "data.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("inner/hello.txt", "hi")
            zf.writestr("outer.txt", "outside")

        result = unzip_file_to_directory(archive)
        assert result is not None
        assert (result / "inner" / "hello.txt").read_text() == "hi"
        assert (result / "outer.txt").read_text() == "outside"

    def test_missing_archive_returns_none(self, tmp_path):
        result = unzip_file_to_directory(tmp_path / "nope.zip")
        assert result is None

    def test_bad_zip_returns_none(self, tmp_path):
        fake = tmp_path / "bad.zip"
        fake.write_text("not a real zip")
        result = unzip_file_to_directory(fake)
        assert result is None
