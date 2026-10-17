"""Failure probes for the #1509 atomic-write review."""

import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from siege_utilities.files import operations
from siege_utilities.files.secure_write import secure_write_text


def test_secure_write_encoding_failure_preserves_private_profile(tmp_path):
    target = tmp_path / "profile.json"
    original = b'{"profile": "old sentinel"}'
    assert len(original) == 27
    target.write_bytes(original)
    target.chmod(0o600)

    with pytest.raises(UnicodeEncodeError):
        secure_write_text(target, '{"new": "\ud800"}')

    assert target.read_bytes() == original
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("operation", ["fsync", "replace"])
@pytest.mark.parametrize("failure", [OSError("disk full"), KeyboardInterrupt()])
def test_secure_write_sync_or_replace_failure_preserves_profile(
    tmp_path, monkeypatch, operation, failure,
):
    target = tmp_path / "profile.json"
    target.write_bytes(b"old profile")
    target.chmod(0o600)

    def fail(*args):
        raise failure

    monkeypatch.setattr(os, operation, fail)
    with pytest.raises(type(failure)):
        secure_write_text(target, "new profile")
    assert target.read_bytes() == b"old profile"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert list(tmp_path.iterdir()) == [target]


def test_secure_write_syncs_private_file_before_publish(tmp_path, monkeypatch):
    target = tmp_path / "profile.json"
    events = []
    real_fsync, real_replace = os.fsync, os.replace

    def sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            events.append("directory")
        else:
            assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o600
            events.append("file")
        real_fsync(fd)

    def replace(source, destination):
        assert Path(source).parent == target.parent
        assert Path(source).read_text() == "new profile"
        assert stat.S_IMODE(Path(source).stat().st_mode) == 0o600
        assert not target.exists()
        events.append("replace")
        real_replace(source, destination)

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "replace", replace)
    secure_write_text(target, "new profile")
    assert events == (["file", "replace", "directory"] if os.name == "posix" else ["file", "replace"])
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


@pytest.mark.parametrize("writer,payload", [
    (operations.safe_json_write, {"a": 1, "b": object()}),
    (operations.safe_file_write, object()),
])
def test_safe_write_failure_preserves_existing_file(tmp_path, writer, payload):
    target = tmp_path / "data.json"
    original = b'{"old": true}\n'
    target.write_bytes(original)

    assert writer(target, payload) is False

    assert target.read_bytes() == original
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("writer,payload", [
    (operations.safe_json_write, {"a": 1}),
    (operations.safe_file_write, "complete"),
])
def test_safe_writes_respect_create_dirs(tmp_path, writer, payload):
    target = tmp_path / "missing" / "data.json"
    assert writer(target, payload, create_dirs=False) is False
    assert not target.parent.exists()
    assert writer(target, payload, create_dirs=True) is True
    assert target.read_text()
    assert list(target.parent.iterdir()) == [target]


class ThreePartWriter:
    def mode(self, mode):
        return self

    def format(self, file_format):
        return self

    def option(self, key, value):
        return self

    def save(self, destination):
        for index in range(3):
            (Path(destination) / f"part-{index}.csv").write_text(f"id\n{index}\n")


@pytest.mark.parametrize("existing", [False, True])
def test_staging_copy_failure_preserves_destination(tmp_path, monkeypatch, existing):
    from siege_utilities.distributed import spark_utils

    final = tmp_path / "final"
    staging = tmp_path / "staging"
    if existing:
        final.mkdir()
        (final / "old.csv").write_bytes(b"old complete data")
    real_copy = spark_utils.shutil.copy2
    copies = []

    def interrupted_copy(source, destination, *args, **kwargs):
        copies.append(destination)
        if len(copies) == 2:
            raise OSError("second copy failed")
        return real_copy(source, destination, *args, **kwargs)

    monkeypatch.setattr(spark_utils.shutil, "copy2", interrupted_copy)
    with pytest.raises(OSError, match="second copy failed"):
        spark_utils.atomic_write_with_staging(
            SimpleNamespace(write=ThreePartWriter()), str(final), str(staging),
        )

    assert len(copies) == 2
    if existing:
        assert sorted(p.name for p in final.iterdir()) == ["old.csv"]
        assert (final / "old.csv").read_bytes() == b"old complete data"
    else:
        assert not final.exists()
    assert sorted(tmp_path.iterdir()) == ([final] if existing else [])


def test_staging_publish_failure_restores_backup(tmp_path, monkeypatch):
    from siege_utilities.distributed import spark_utils

    final = tmp_path / "final"
    final.mkdir()
    (final / "old.csv").write_bytes(b"old complete data")
    real_replace = os.replace

    def fail_publication(source, destination):
        if Path(source).name.startswith(".final_staging_"):
            assert sorted(p.name for p in Path(source).iterdir()) == [
                "part-0.csv", "part-1.csv", "part-2.csv",
            ]
            raise OSError("publication failed")
        real_replace(source, destination)

    monkeypatch.setattr(spark_utils.os, "replace", fail_publication)
    with pytest.raises(OSError, match="publication failed"):
        spark_utils.atomic_write_with_staging(
            SimpleNamespace(write=ThreePartWriter()), str(final), str(tmp_path / "staging"),
        )
    assert (final / "old.csv").read_bytes() == b"old complete data"
    assert list(tmp_path.iterdir()) == [final]


@pytest.mark.parametrize("existing", ["absent", "empty", "nonempty"])
def test_staging_publishes_all_parts_together(tmp_path, monkeypatch, existing):
    from siege_utilities.distributed import spark_utils

    final = tmp_path / "final"
    staging = tmp_path / "staging"
    if existing != "absent":
        final.mkdir()
    if existing == "nonempty":
        (final / "old.csv").write_bytes(b"old complete data")
    real_replace = os.replace
    publications = []

    def replace(source, destination):
        if Path(source).name.startswith(".final_staging_"):
            assert Path(source).parent == final.parent
            assert sorted(p.name for p in Path(source).iterdir()) == [
                "part-0.csv", "part-1.csv", "part-2.csv",
            ]
            publications.append(destination)
        real_replace(source, destination)

    monkeypatch.setattr(spark_utils.os, "replace", replace)
    spark_utils.atomic_write_with_staging(
        SimpleNamespace(write=ThreePartWriter()), str(final), str(staging),
    )
    assert publications == [final]
    for index in range(3):
        assert (final / f"part-{index}.csv").read_text() == f"id\n{index}\n"
    assert not staging.exists()
    assert not list(tmp_path.glob(".final_staging_*"))
    backups = list(tmp_path.glob("final_backup_*"))
    assert len(backups) == (1 if existing == "nonempty" else 0)
    if backups:
        assert (backups[0] / "old.csv").read_bytes() == b"old complete data"
