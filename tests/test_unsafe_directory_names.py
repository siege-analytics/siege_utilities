"""Every public helper that creates a directory refuses unsafe new names (#1716).

A directory component that does not exist yet may not contain a C0 control,
DEL, a C1 control or a lone surrogate (how undecodable bytes reach Python).
Each refusal raises PathSecurityError and leaves the filesystem untouched.
Readers that never create anything keep their pre-#1710 not-found behaviour.
"""

import logging
import os
import shutil
from pathlib import Path

import pytest

from siege_utilities.config import directories, projects
from siege_utilities.files import formats, operations, paths, remote
from siege_utilities.files.validation import (
    PathSecurityError,
    reject_unsafe_new_directory_names,
    validate_directory_path,
)

# The helpers log the paths they are given. Captured log lines and warnings
# travel in each test report, and xdist cannot send a lone surrogate over its
# UTF-8 channel, so this module emits neither; it asserts on exceptions and
# on the filesystem only.
pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(autouse=True)
def _no_log_output():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture(autouse=True)
def _remove_tmp_path(tmp_path):
    # A regression would leave control-character directories behind, the
    # names that crashed file watchers in #1690; remove them even on failure.
    yield
    shutil.rmtree(tmp_path, ignore_errors=True)


def _tabular_frame():
    pandas = pytest.importorskip("pandas")
    return pandas.DataFrame({"a": [1]})


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
    "save_spatial": lambda root, target: formats.save_spatial(None, target / "f.parquet"),
    "save_tabular": lambda root, target: formats.save_tabular(_tabular_frame(), target / "f.parquet"),
}

try:  # develop only; private, but config and credential exporters write through it
    from siege_utilities.files.secure_write import secure_write_text
except ImportError:
    pass
else:
    CREATORS["secure_write_text"] = lambda root, target: secure_write_text(target / "f.txt", "x")


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
        # The last shape: mkdir creates <bad> on the way even though ".." cancels it.
        for parts in ((bad, "b", "c"), ("a", bad, "c"), ("a", "b", bad), (ch,), ("a", bad, "..", "c")):
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
    if creator in ("atomic_write_shapefile", "save_spatial"):
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


WRITERS = ["atomic_write_path", "save_tabular", "secure_write_text"]


def _write(creator, target):
    if creator == "atomic_write_path":
        with operations.atomic_write_path(target / "f.csv") as tmp:
            tmp.write_text("x")
        return target / "f.csv"
    if creator == "save_tabular":
        return formats.save_tabular(_tabular_frame(), target / "f.parquet")
    CREATORS[creator](None, target)
    return target / "f.txt"


@pytest.mark.parametrize("creator", WRITERS)
def test_dotdot_path_is_written_as_given_and_stays_usable(creator, tmp_path, monkeypatch):
    """A legitimate ``x/new/../y`` behaves as before #1716: ``new`` is created
    and the path the caller holds still opens (review of #1718, round 2)."""
    if creator not in CREATORS:
        pytest.skip(f"{creator} is not on this branch")
    monkeypatch.chdir(tmp_path)
    written = _write(creator, Path("x") / "new" / ".." / "y")
    assert (tmp_path / "x" / "new").is_dir()
    assert Path(written).is_file()
    assert written == Path("x") / "new" / ".." / "y" / Path(written).name


@pytest.mark.parametrize("creator", WRITERS)
def test_dangling_symlink_parent_fails_closed(creator, tmp_path, monkeypatch):
    """A dangling symlink in the parent is not followed: the write fails and
    the link's target is not created (review of #1718, round 2)."""
    if creator not in CREATORS:
        pytest.skip(f"{creator} is not on this branch")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dangling").symlink_to(tmp_path / "elsewhere" / "deep")
    with pytest.raises(OSError):
        _write(creator, tmp_path / "dangling")
    assert not (tmp_path / "elsewhere").exists()


# Zip member names are stored as UTF-8 or cp437, so they cannot carry surrogates.
ZIP_UNSAFE = [ch for ch in UNSAFE if not "\ud800" <= ch <= "\udfff"]


@pytest.mark.parametrize("as_directory_entry", [False, True], ids=["file-entry", "dir-entry"])
@pytest.mark.parametrize("create_subdirectory", [False, True], ids=["flat", "subdir"])
def test_archive_member_directories_are_checked(as_directory_entry, create_subdirectory, tmp_path):
    """An archive that would create an unsafe directory is refused before
    anything is extracted (CodeRabbit on #1719)."""
    import zipfile

    created = []
    for i, ch in enumerate(ZIP_UNSAFE):
        archive = tmp_path / f"a{i}.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("ok.txt", "x")
            z.writestr(f"p{ch}q/" if as_directory_entry else f"p{ch}q/x.txt", "" if as_directory_entry else "x")
        out = tmp_path / f"out{i}"
        out.mkdir()
        with pytest.raises(PathSecurityError):
            paths.unzip_file_to_directory(archive, out, create_subdirectory=create_subdirectory)
        if os.listdir(out):
            created.append((repr(ch), os.listdir(out)))
    assert created == [], created[:3]


def test_archive_with_ordinary_member_directories_still_extracts(tmp_path):
    import zipfile

    archive = tmp_path / "ok.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("café é/数据/x.txt", "x")
        z.writestr("empty dir/", "")
    out = tmp_path / "out"
    extracted = paths.unzip_file_to_directory(archive, out, create_subdirectory=False)
    assert (extracted / "café é" / "数据" / "x.txt").read_text() == "x"
    assert (extracted / "empty dir").is_dir()


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

    @pytest.mark.parametrize("ch", ["\x1b", "\x7f", "\x85", "\udc80"], ids=lambda ch: f"U+{ord(ch):04X}")
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
