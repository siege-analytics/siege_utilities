"""Every public helper that creates a directory refuses unsafe new names (#1716).

A directory component that does not exist yet may not contain a C0 control,
DEL, a C1 control or a lone surrogate (how undecodable bytes reach Python).
Each refusal raises PathSecurityError and leaves the filesystem untouched.
Readers that never create anything keep their pre-#1710 not-found behaviour.
"""

import os
from pathlib import Path

import pytest

from siege_utilities.config import directories, projects
from siege_utilities.files import operations, paths, remote
from siege_utilities.files.validation import (
    PathSecurityError,
    reject_unsafe_new_directory_names,
    validate_directory_path,
)

UNSAFE = (
    [chr(c) for c in range(1, 0x20)]  # NUL is refused earlier, as a null byte
    + ["\x7f"]
    + [chr(c) for c in range(0x80, 0xA0)]
    + ["\udc80", "\udc9b", "\udcff"]  # surrogateescape: undecodable bytes
)
# Surrogates outside the escape range cannot be encoded at all.
UNENCODABLE = ["\ud800", "\udbff", "\udfff"]


def _source(root: Path) -> Path:
    return root / "source.txt"


# Each entry creates the directory ``target`` (or a file directly inside it).
CREATORS = {
    "validate_then_mkdir": lambda root, target: validate_directory_path(target).mkdir(parents=True),
    "reject_unsafe_new_directory_names": lambda root, target: reject_unsafe_new_directory_names(target),
    "ensure_path_exists": lambda root, target: paths.ensure_path_exists(target),
    "ensure_directory_exists": lambda root, target: operations.ensure_directory_exists(target),
    "touch_file": lambda root, target: operations.touch_file(target / "f.txt"),
    "copy_file": lambda root, target: operations.copy_file(_source(root), target / "f.txt"),
    "move_file": lambda root, target: operations.move_file(_source(root), target / "f.txt"),
    "replace_with_empty_file": lambda root, target: (
        operations.delete_existing_file_and_replace_it_with_an_empty_file(target / "f.txt")
    ),
    "safe_file_write": lambda root, target: operations.safe_file_write(target / "f.txt", "x"),
    "safe_json_write": lambda root, target: operations.safe_json_write(target / "f.json", {}),
    "atomic_write_path": lambda root, target: operations.atomic_write_path(target / "f.csv").__enter__(),
    "atomic_write_shapefile": lambda root, target: operations.atomic_write_shapefile(None, target / "f.shp"),
    "download_file": lambda root, target: remote.download_file("https://example.invalid/f", target / "f"),
}


def _snapshot(root: Path):
    return sorted(os.path.relpath(os.path.join(d, n), root)
                  for d, dirs, files in os.walk(root) for n in dirs + files)


@pytest.mark.parametrize("creator", sorted(CREATORS))
def test_unsafe_new_component_is_refused_and_nothing_is_created(creator, tmp_path, monkeypatch):
    if creator == "download_file":
        pytest.importorskip("requests")
    create = CREATORS[creator]
    created = []
    case = 0
    for ch in UNSAFE:
        bad = f"p{ch}q"
        for parts in ((bad, "b", "c"), ("a", bad, "c"), ("a", "b", bad), (ch,)):
            for absolute in (True, False):
                case += 1
                root = tmp_path / f"case{case}"
                root.mkdir()
                _source(root).write_text("x")
                before = _snapshot(root)
                monkeypatch.chdir(root)
                target = (root if absolute else Path()).joinpath(*parts)
                with pytest.raises(PathSecurityError):
                    create(root, target)
                after = _snapshot(root)
                if after != before:
                    created.append((repr(ch), parts, absolute, after))
                monkeypatch.chdir(tmp_path)
    assert created == [], f"{creator} created entries for {len(created)} cases, e.g. {created[:3]}"


@pytest.mark.parametrize("creator", sorted(CREATORS))
def test_ordinary_names_still_work(creator, tmp_path, monkeypatch):
    if creator == "download_file":
        pytest.skip("needs the network once the parent exists")
    if creator == "atomic_write_shapefile":
        pytest.skip("needs a GeoDataFrame once the parent exists")
    if creator == "reject_unsafe_new_directory_names":
        pytest.skip("checks names only; creates nothing")
    monkeypatch.chdir(tmp_path)
    for name in ("plain", "café é", "数据", "📁 emoji", "a#b", "back\\slash", "nb\u00a0sp", "שלום"):
        target = tmp_path / name / "sub"
        _source(tmp_path).write_text("x")
        CREATORS[creator](tmp_path, target)
        assert target.is_dir(), (creator, name)


@pytest.mark.parametrize("creator", sorted(CREATORS))
def test_unencodable_names_create_nothing(creator, tmp_path, monkeypatch):
    if creator == "download_file":
        pytest.importorskip("requests")
    monkeypatch.chdir(tmp_path)
    _source(tmp_path).write_text("x")
    for ch in UNENCODABLE:
        with pytest.raises((PathSecurityError, ValueError)):
            CREATORS[creator](tmp_path, tmp_path / f"p{ch}q" / "c")
    assert os.listdir(tmp_path) == ["source.txt"]


def test_existing_directory_with_unsafe_name_still_accepted(tmp_path):
    existing = tmp_path / "odd\x16name"
    existing.mkdir()
    try:
        assert operations.ensure_directory_exists(existing) == existing.resolve()
        assert operations.safe_file_write(existing / "child" / "f.txt", "x")
    finally:
        # Never leave a control-character name behind for watchers (#1690).
        for dirpath, dirnames, filenames in os.walk(existing, topdown=False):
            for name in filenames:
                os.unlink(os.path.join(dirpath, name))
            for name in dirnames:
                os.rmdir(os.path.join(dirpath, name))
        existing.rmdir()


class TestReadersKeepNotFoundBehaviour:
    """Readers create nothing, so a missing unsafe name is simply not found."""

    # Control characters only: the readers log the missing path, and a
    # surrogate in captured output cannot cross xdist's UTF-8 channel.
    @pytest.mark.parametrize("ch", ["\x1b", "\x7f", "\x85"], ids=lambda ch: f"U+{ord(ch):04X}")
    def test_readers(self, ch, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        missing = str(tmp_path / f"no{ch}such")
        assert directories.get_directory_info(missing) == {}
        assert directories.load_directory_config("x", config_directory=missing) is None
        assert directories.list_directory_configs(config_directory=missing) == []
        assert projects.list_projects(config_directory=missing) == []
        with pytest.raises(FileNotFoundError):
            projects.load_project_config("x", config_directory=missing)
        assert os.listdir(tmp_path) == []
