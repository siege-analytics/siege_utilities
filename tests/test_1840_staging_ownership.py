"""Regression tests for #1840: staging must not destroy caller-owned files.

``atomic_write_with_staging`` used to ``rmtree`` the caller's
``staging_directory`` before writing and again in ``finally``, so a failed
write still deleted whatever the caller kept there, and two calls sharing one
staging directory could delete or publish each other's files. Each call now
writes into its own unique child of ``staging_directory`` and removes only
what it created.

Writing to a fresh child also means Spark's save mode no longer sees an
existing directory, so the mode is honoured at the final destination
instead: ``error``/``errorifexists`` refuse an existing destination and
``ignore`` leaves it untouched.
"""

import os
import stat
from pathlib import Path
from unittest.mock import Mock

import pytest

from siege_utilities.distributed.spark_utils import atomic_write_with_staging


class SavingWriter:
    """Fake ``DataFrameWriter`` that writes one CSV part file on ``save``."""

    def __init__(self, fail=False):
        self.fail = fail
        self.saved_to = []
        self.modes = []

    def mode(self, value):
        self.modes.append(value)
        return self

    def format(self, value):
        return self

    def option(self, key, value):
        return self

    def save(self, destination):
        self.saved_to.append(destination)
        Path(destination).mkdir(parents=True, exist_ok=True)
        Path(destination, "part-00000.csv").write_text("id\n1\n")
        if self.fail:
            raise RuntimeError("injected writer failure")


def _df(writer):
    df = Mock()
    df.write = writer
    return df


def _tree(root):
    """Snapshot every path under ``root`` with its type and file content."""
    found = {}
    for path in sorted(Path(root).rglob("*")):
        rel = str(path.relative_to(root))
        if path.is_symlink():
            found[rel] = "link:" + os.readlink(path)
        elif path.is_dir():
            found[rel] = "dir"
        else:
            found[rel] = path.read_bytes()
    return found


def _caller_staging(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    sentinel = staging / "caller_sentinel.txt"
    sentinel.write_text("caller data")
    return staging, sentinel


def test_writer_failure_keeps_caller_sentinel(tmp_path):
    """The reviewer's fixture: an injected writer failure after staging."""
    staging, sentinel = _caller_staging(tmp_path)
    final = tmp_path / "final"

    with pytest.raises(RuntimeError, match="injected writer failure"):
        atomic_write_with_staging(_df(SavingWriter(fail=True)), str(final), str(staging))

    assert sentinel.read_text() == "caller data"
    assert sorted(p.name for p in staging.iterdir()) == ["caller_sentinel.txt"]
    assert not final.exists()


def test_success_keeps_caller_sentinel_and_publishes_only_new_output(tmp_path):
    staging, sentinel = _caller_staging(tmp_path)
    final = tmp_path / "final"

    atomic_write_with_staging(_df(SavingWriter()), str(final), str(staging))

    assert sentinel.read_text() == "caller data"
    assert sorted(p.name for p in staging.iterdir()) == ["caller_sentinel.txt"]
    assert sorted(p.name for p in final.iterdir()) == ["part-00000.csv"]


def test_spark_writes_to_unique_child_of_staging(tmp_path):
    staging, _ = _caller_staging(tmp_path)
    writer = SavingWriter()

    atomic_write_with_staging(_df(writer), str(tmp_path / "a"), str(staging))
    atomic_write_with_staging(_df(writer), str(tmp_path / "b"), str(staging))

    first, second = (Path(p) for p in writer.saved_to)
    assert first.parent == staging and second.parent == staging
    assert first != second
    assert not first.exists() and not second.exists()


def test_staging_created_by_call_is_removed_on_failure(tmp_path):
    staging = tmp_path / "fresh_staging"

    with pytest.raises(RuntimeError):
        atomic_write_with_staging(
            _df(SavingWriter(fail=True)), str(tmp_path / "final"), str(staging)
        )

    assert not staging.exists()


def test_staging_created_by_call_is_removed_on_success(tmp_path):
    staging = tmp_path / "fresh_staging"

    atomic_write_with_staging(_df(SavingWriter()), str(tmp_path / "final"), str(staging))

    assert not staging.exists()


def test_existing_empty_caller_staging_is_left_in_place(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()

    atomic_write_with_staging(_df(SavingWriter()), str(tmp_path / "final"), str(staging))

    assert staging.is_dir()
    assert list(staging.iterdir()) == []


def test_staging_path_that_is_a_file_raises_file_exists_error(tmp_path):
    staging = tmp_path / "staging_file"
    staging.write_text("not a directory")
    writer = SavingWriter()

    with pytest.raises(FileExistsError):
        atomic_write_with_staging(_df(writer), str(tmp_path / "final"), str(staging))

    assert staging.read_text() == "not a directory"
    assert writer.saved_to == []
    assert not (tmp_path / "final").exists()


def test_staging_created_by_call_keeps_another_writers_file(tmp_path):
    """Pins os.rmdir (not rmtree) for a staging directory this call created."""
    staging = tmp_path / "fresh_staging"

    class WriterWithNeighbour(SavingWriter):
        def save(self, destination):
            super().save(destination)
            (staging / "other_writer.txt").write_text("not ours")

    atomic_write_with_staging(_df(WriterWithNeighbour()), str(tmp_path / "final"), str(staging))

    assert [path.name for path in staging.iterdir()] == ["other_writer.txt"]
    assert (staging / "other_writer.txt").read_text() == "not ours"


def test_staging_created_concurrently_by_another_party_is_not_removed(tmp_path, monkeypatch):
    """Ownership is decided by os.makedirs itself, so there is no check-then-create race."""
    from siege_utilities.distributed import spark_utils

    staging = tmp_path / "raced_staging"
    real_makedirs = os.makedirs

    def other_party_creates_it_first(path, *args, **kwargs):
        if Path(path) == staging and not staging.exists():
            staging.mkdir()
        return real_makedirs(path, *args, **kwargs)

    monkeypatch.setattr(spark_utils.os, "makedirs", other_party_creates_it_first)

    atomic_write_with_staging(_df(SavingWriter()), str(tmp_path / "final"), str(staging))

    assert staging.is_dir() and list(staging.iterdir()) == []


def test_published_directory_mode_comes_from_the_written_output(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    os.chmod(staging, 0o700)
    reference = tmp_path / "reference"
    reference.mkdir()
    expected = stat.S_IMODE(reference.stat().st_mode)
    reference.rmdir()
    assert expected != 0o700, "umask makes this test vacuous"

    atomic_write_with_staging(_df(SavingWriter()), str(tmp_path / "final"), str(staging))

    assert stat.S_IMODE((tmp_path / "final").stat().st_mode) == expected


def test_writer_that_does_not_create_its_destination_gets_file_not_found(tmp_path):
    class NonCreatingWriter(SavingWriter):
        def save(self, destination):
            Path(destination, "part-00000.csv").write_text("id\n1\n")

    with pytest.raises(FileNotFoundError):
        atomic_write_with_staging(
            _df(NonCreatingWriter()), str(tmp_path / "final"), str(tmp_path / "staging")
        )

    assert not (tmp_path / "final").exists()


# --- the save mode is honoured at the final destination --------------------


def _existing_final(tmp_path):
    final = tmp_path / "final"
    final.mkdir()
    (final / "old.csv").write_text("old data")
    return final


@pytest.mark.parametrize("mode", ["error", "errorifexists", "ERROR"])
def test_error_modes_refuse_an_existing_destination(tmp_path, mode):
    final = _existing_final(tmp_path)
    writer = SavingWriter()

    with pytest.raises(FileExistsError, match="already exists"):
        atomic_write_with_staging(_df(writer), str(final), str(tmp_path / "staging"), mode=mode)

    assert sorted(p.name for p in final.iterdir()) == ["old.csv"]
    assert (final / "old.csv").read_text() == "old data"
    assert writer.saved_to == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["final"]


def test_error_mode_refuses_an_existing_empty_destination(tmp_path):
    final = tmp_path / "final"
    final.mkdir()

    with pytest.raises(FileExistsError):
        atomic_write_with_staging(
            _df(SavingWriter()), str(final), str(tmp_path / "staging"), mode="errorifexists"
        )

    assert list(final.iterdir()) == []


def test_ignore_mode_leaves_an_existing_destination_untouched(tmp_path):
    final = _existing_final(tmp_path)
    writer = SavingWriter()

    atomic_write_with_staging(_df(writer), str(final), str(tmp_path / "staging"), mode="ignore")

    assert sorted(p.name for p in final.iterdir()) == ["old.csv"]
    assert (final / "old.csv").read_text() == "old data"
    assert writer.saved_to == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["final"]


@pytest.mark.parametrize("mode", ["error", "errorifexists", "ignore", "overwrite", "append"])
def test_every_mode_publishes_to_an_absent_destination(tmp_path, mode):
    final = tmp_path / "final"

    atomic_write_with_staging(_df(SavingWriter()), str(final), str(tmp_path / "staging"), mode=mode)

    assert sorted(p.name for p in final.iterdir()) == ["part-00000.csv"]


@pytest.mark.parametrize("destination", ["existing", "absent"])
@pytest.mark.parametrize("mode", [None, "default", "Default", "bogus", "", 5],
                         ids=["None", "default", "Default", "bogus", "empty", "int"])
def test_unsupported_mode_is_rejected_before_anything_is_written(tmp_path, mode, destination):
    """Spark reads ``'default'`` (and pyspark reads ``None``) as errorifexists.

    Passed through to a fresh staging child they would never refuse, so the
    old destination would be replaced. They are rejected instead, like any
    other value outside the five documented modes.
    """
    final = tmp_path / "final"
    if destination == "existing":
        final.mkdir()
        (final / "old.csv").write_text("old data")
    before = _tree(tmp_path)
    writer = SavingWriter()

    with pytest.raises(ValueError, match="mode"):
        atomic_write_with_staging(_df(writer), str(final), str(tmp_path / "staging"), mode=mode)

    assert writer.saved_to == []
    assert _tree(tmp_path) == before


@pytest.mark.parametrize("mode", ["error", "errorifexists", "ignore"])
@pytest.mark.parametrize("shape", ["file", "dangling_symlink"])
def test_refusing_modes_see_a_destination_that_is_not_a_directory(tmp_path, mode, shape):
    final = tmp_path / "final"
    if shape == "file":
        final.write_text("a plain file")
    else:
        final.symlink_to(tmp_path / "nowhere")
    before = _tree(tmp_path)
    writer = SavingWriter()

    if mode == "ignore":
        atomic_write_with_staging(_df(writer), str(final), str(tmp_path / "staging"), mode=mode)
    else:
        with pytest.raises(FileExistsError):
            atomic_write_with_staging(_df(writer), str(final), str(tmp_path / "staging"), mode=mode)

    assert writer.saved_to == []
    assert _tree(tmp_path) == before


def test_ignore_mode_logs_that_it_wrote_nothing(tmp_path, monkeypatch):
    from siege_utilities.distributed import spark_utils

    final = tmp_path / "final"
    final.mkdir()
    messages = []
    monkeypatch.setattr(spark_utils, "log_info", lambda message, *a, **k: messages.append(message))

    atomic_write_with_staging(_df(SavingWriter()), str(final), str(tmp_path / "staging"), mode="ignore")

    assert len(messages) == 1
    assert str(final) in messages[0] and "writes nothing" in messages[0]


@pytest.mark.parametrize("mode", ["overwrite", "append", "error", "errorifexists", "ignore"])
def test_mode_is_passed_to_the_writer(tmp_path, mode):
    writer = SavingWriter()

    atomic_write_with_staging(_df(writer), str(tmp_path / "final"), str(tmp_path / "staging"), mode=mode)

    assert writer.modes == [mode]


@pytest.mark.parametrize("mode", ["error", "errorifexists", "ignore"])
@pytest.mark.parametrize("missing", ["the_staging_directory", "another_directory"])
def test_refusing_modes_see_a_destination_spelled_through_a_missing_directory(tmp_path, mode, missing):
    """``<missing>/../final`` is absent to the OS until ``<missing>`` exists.

    This call creates ``<missing>`` itself (the staging directory, or the
    destination's parent), after which the same string names the existing
    destination. Spark resolves ``..`` lexically and refuses such a path.
    """
    final = _existing_final(tmp_path)
    staging = tmp_path / "staging"
    middle = staging if missing == "the_staging_directory" else tmp_path / "run_42"
    spelled = os.path.join(str(middle), "..", "final")
    before = _tree(tmp_path)
    writer = SavingWriter()

    if mode == "ignore":
        atomic_write_with_staging(_df(writer), spelled, str(staging), mode=mode)
    else:
        with pytest.raises(FileExistsError):
            atomic_write_with_staging(_df(writer), spelled, str(staging), mode=mode)

    assert writer.saved_to == []
    assert _tree(tmp_path) == before
    assert (final / "old.csv").read_text() == "old data"


@pytest.mark.parametrize("mode", ["error", "errorifexists", "ignore"])
@pytest.mark.parametrize("shape", ["file", "dangling_symlink"])
def test_refusing_modes_see_a_non_directory_destination_with_a_trailing_slash(tmp_path, mode, shape):
    final = tmp_path / "final"
    if shape == "file":
        final.write_text("a plain file")
    else:
        final.symlink_to(tmp_path / "nowhere")
    before = _tree(tmp_path)
    writer = SavingWriter()

    if mode == "ignore":
        atomic_write_with_staging(_df(writer), str(final) + "/", str(tmp_path / "staging"), mode=mode)
    else:
        with pytest.raises(FileExistsError):
            atomic_write_with_staging(_df(writer), str(final) + "/", str(tmp_path / "staging"), mode=mode)

    assert writer.saved_to == []
    assert _tree(tmp_path) == before


@pytest.mark.parametrize("mode", ["error", "errorifexists", "ignore"])
@pytest.mark.parametrize("existing", ["os_reading", "lexical_reading"])
def test_refusing_modes_see_a_destination_spelled_through_a_symlink(tmp_path, mode, existing):
    """``link/../final`` names two paths when ``link`` is a symlink.

    The OS follows the link first (``deep/inner/..`` is ``deep``), giving
    ``deep/final``; Spark and ``normpath`` drop ``link/..`` lexically, giving
    ``final`` beside the link. Whichever of the two exists, the refusing modes
    must leave it alone.
    """
    (tmp_path / "deep" / "inner").mkdir(parents=True)
    (tmp_path / "link").symlink_to(tmp_path / "deep" / "inner")
    target = tmp_path / "deep" / "final" if existing == "os_reading" else tmp_path / "final"
    target.mkdir()
    (target / "old.csv").write_text("old data")
    spelled = os.path.join(str(tmp_path / "link"), "..", "final")
    before = _tree(tmp_path)
    writer = SavingWriter()

    if mode == "ignore":
        atomic_write_with_staging(_df(writer), spelled, str(tmp_path / "staging"), mode=mode)
    else:
        with pytest.raises(FileExistsError):
            atomic_write_with_staging(_df(writer), spelled, str(tmp_path / "staging"), mode=mode)

    assert writer.saved_to == []
    assert _tree(tmp_path) == before


@pytest.mark.parametrize("mode", ["overwrite", "append"])
def test_overwrite_and_append_replace_an_existing_destination(tmp_path, mode):
    final = _existing_final(tmp_path)

    atomic_write_with_staging(_df(SavingWriter()), str(final), str(tmp_path / "staging"), mode=mode)

    assert sorted(p.name for p in final.iterdir()) == ["part-00000.csv"]


@pytest.mark.e2e
def test_real_spark_write_keeps_caller_staging_contents(real_spark_session, tmp_path):
    staging, sentinel = _caller_staging(tmp_path)
    final = tmp_path / "final"
    df = real_spark_session.createDataFrame([(1, "a"), (2, "b")], ["id", "name"])

    atomic_write_with_staging(df, str(final), str(staging), file_format="parquet")

    assert sentinel.read_text() == "caller data"
    assert sorted(p.name for p in staging.iterdir()) == ["caller_sentinel.txt"]
    assert not (final / "caller_sentinel.txt").exists()
    assert real_spark_session.read.parquet(str(final)).count() == 2


@pytest.mark.e2e
@pytest.mark.parametrize("mode", ["error", "errorifexists"])
def test_real_spark_error_modes_refuse_existing_destination(real_spark_session, tmp_path, mode):
    final = _existing_final(tmp_path)
    df = real_spark_session.createDataFrame([(1, "a")], ["id", "name"])

    with pytest.raises(FileExistsError):
        atomic_write_with_staging(df, str(final), str(tmp_path / "staging"), mode=mode)

    assert sorted(p.name for p in final.iterdir()) == ["old.csv"]
    assert (final / "old.csv").read_text() == "old data"


@pytest.mark.e2e
@pytest.mark.parametrize("mode", ["error", "errorifexists", "ignore"])
def test_real_spark_modes_publish_to_an_absent_destination(real_spark_session, tmp_path, mode):
    """6.0.0 raised for error modes and published an empty directory for ignore here."""
    final = tmp_path / "final"
    df = real_spark_session.createDataFrame([(1, "a"), (2, "b")], ["id", "name"])

    atomic_write_with_staging(df, str(final), str(tmp_path / "staging"),
                              file_format="parquet", mode=mode)

    assert real_spark_session.read.parquet(str(final)).count() == 2


@pytest.mark.e2e
def test_real_spark_ignore_mode_leaves_existing_destination(real_spark_session, tmp_path):
    final = _existing_final(tmp_path)
    df = real_spark_session.createDataFrame([(1, "a")], ["id", "name"])

    atomic_write_with_staging(df, str(final), str(tmp_path / "staging"), mode="ignore")

    assert sorted(p.name for p in final.iterdir()) == ["old.csv"]
    assert (final / "old.csv").read_text() == "old data"


@pytest.mark.e2e
@pytest.mark.parametrize("mode", ["error", "errorifexists", "ignore"])
def test_real_spark_refusing_modes_keep_a_destination_spelled_through_dotdot(
    real_spark_session, tmp_path, mode
):
    final = tmp_path / "final"
    real_spark_session.range(3).write.parquet(str(final))
    staging = tmp_path / "staging"
    spelled = os.path.join(str(staging), "..", "final")
    df = real_spark_session.range(5)

    if mode == "ignore":
        atomic_write_with_staging(df, spelled, str(staging), file_format="parquet", mode=mode)
    else:
        with pytest.raises(FileExistsError):
            atomic_write_with_staging(df, spelled, str(staging), file_format="parquet", mode=mode)

    assert real_spark_session.read.parquet(str(final)).count() == 3
    assert not list(tmp_path.glob("final_backup_*"))


@pytest.mark.parametrize("mode", ["error", "errorifexists", "ignore"])
def test_refusing_modes_see_a_destination_spelled_through_a_link_to_the_missing_staging_directory(tmp_path, mode):
    """``current/../final`` where ``current`` links to the staging directory.

    Until this call creates the staging directory the link dangles, so the OS
    cannot resolve the string, and its lexical reading (``data/final``) is
    absent. Once the directory exists the same string names ``runs/final``.
    """
    data = tmp_path / "data"
    data.mkdir()
    final = tmp_path / "runs" / "final"
    final.mkdir(parents=True)
    (final / "old.csv").write_text("old data")
    staging = tmp_path / "runs" / "run_42"
    (data / "current").symlink_to(staging)
    spelled = os.path.join(str(data / "current"), "..", "final")
    before = _tree(tmp_path)
    writer = SavingWriter()

    if mode == "ignore":
        atomic_write_with_staging(_df(writer), spelled, str(staging), mode=mode)
    else:
        with pytest.raises(FileExistsError):
            atomic_write_with_staging(_df(writer), spelled, str(staging), mode=mode)

    assert writer.saved_to == []
    assert _tree(tmp_path) == before
    assert (final / "old.csv").read_text() == "old data"
