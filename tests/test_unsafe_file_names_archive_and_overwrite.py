"""#1737 review follow-ups: archive members are checked where zipfile writes
them, and existing unsafe files stay writable, readable and movable."""
import os
import zipfile

import pytest

from siege_utilities.files import operations, paths
from siege_utilities.files.validation import PathSecurityError


@pytest.mark.parametrize("ch", ["\x1b", "\n", "\x85"], ids=["ESC", "LF", "NEL"])
def test_archive_member_is_checked_where_zipfile_writes_it(ch, tmp_path):
    """zipfile.extract drops '..' parts, so 'a/../f<ch>.txt' lands at a/f<ch>.txt.
    The check must look at that path, not at the existing <target>/f<ch>.txt."""
    target = tmp_path / "t"
    (target / "a").mkdir(parents=True)
    (target / f"f{ch}.txt").write_text("pre-existing")
    archive = tmp_path / "z.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(f"a/../f{ch}.txt", "x")
    try:
        with pytest.raises(PathSecurityError):
            paths.unzip_file_to_directory(archive, target, create_subdirectory=False)
        assert os.listdir(target / "a") == []
    finally:
        for p in (target / "a" / f"f{ch}.txt", target / f"f{ch}.txt"):
            p.unlink(missing_ok=True)


@pytest.mark.parametrize("ch", ["\x16", "\x85", "\udcff"], ids=["SYN", "NEL", "SURR"])
def test_existing_unsafe_file_is_rewritten_read_and_moved_from(ch, tmp_path):
    odd = tmp_path / f"odd{ch}.csv"
    odd.write_text("old")
    try:
        assert operations.safe_file_write(odd, "new") is True
        assert operations.safe_file_read(odd) == "new"
        with operations.atomic_write_path(odd) as tmp:
            tmp.write_text("newer")
        assert odd.read_text() == "newer"
        operations.move_file(odd, tmp_path / "moved.csv")
        assert (tmp_path / "moved.csv").read_text() == "newer"
    finally:
        odd.unlink(missing_ok=True)


def test_archive_with_dotdot_and_safe_name_still_extracts(tmp_path):
    """The write-path check must not refuse ordinary members that use '..'."""
    target = tmp_path / "t"
    (target / "a").mkdir(parents=True)
    archive = tmp_path / "z.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("a/../ok.txt", "x")
        z.writestr("b/c.txt", "y")
    paths.unzip_file_to_directory(archive, target, create_subdirectory=False)
    assert (target / "a" / "ok.txt").read_text() == "x"
    assert (target / "b" / "c.txt").read_text() == "y"


@pytest.mark.parametrize("shape", ["absolute_inside", "dotdot_reentry"])
def test_other_member_shapes_landing_on_an_unsafe_name_are_refused(shape, tmp_path):
    """An absolute member that resolves inside the target, and '../t/f<ESC>.txt',
    are also written under the target with an unsafe name; both are refused."""
    target = tmp_path / "t"
    target.mkdir()
    (target / "f\x1b.txt").write_text("pre-existing")
    member = (str(target / "f\x1b.txt") if shape == "absolute_inside" else "../t/f\x1b.txt")
    archive = tmp_path / "z.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(member, "x")
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    try:
        with pytest.raises(PathSecurityError):
            paths.unzip_file_to_directory(archive, target, create_subdirectory=False)
        assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*")) == before
    finally:
        for p in list(tmp_path.rglob("*\x1b*")):
            if p.is_file():
                p.unlink()
        for p in sorted(tmp_path.rglob("*\x1b*"), reverse=True):
            if p.is_dir():
                p.rmdir()
