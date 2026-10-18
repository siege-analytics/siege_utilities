"""Regression coverage for Spark output living outside the driver's disk."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from siege_utilities.distributed import spark_utils
from tests.hadoop_fs_support import (
    HadoopFileSystem, HadoopPath, HadoopWriter, dataframe,
)


@pytest.mark.parametrize("uri", ["hdfs://namenode", "s3a://bucket", "abfss://container@account", "dbfs://"])
@pytest.mark.parametrize("qualified", [False, True])
def test_promotes_output_on_spark_filesystem(tmp_path, uri, qualified):
    fs = HadoopFileSystem(uri, tmp_path / "remote")
    # The same scheme-less strings resolve to a different root in Spark.
    staging = str(tmp_path / "driver" / "staging")
    final = str(tmp_path / "driver" / "final")
    if qualified:
        staging, final = uri + staging, uri + final

    spark_utils.atomic_write_with_staging(dataframe(fs), final, staging)

    assert (fs.local(final) / "part-00000.csv").read_text() == "id,name\n1,Ada\n"
    assert not fs.local(staging).exists()
    assert not (tmp_path / "driver").exists()
    assert not Path("s3a:").exists()
    assert len(fs.renames) == 1


def test_file_uri_promotes_to_local_disk(tmp_path):
    fs = HadoopFileSystem("file://")
    final, staging = tmp_path / "final", tmp_path / "staging"

    spark_utils.atomic_write_with_staging(dataframe(fs), final.as_uri(), staging.as_uri())

    assert (final / "part-00000.csv").read_text() == "id,name\n1,Ada\n"
    assert not staging.exists()
    assert not Path("file:").exists()


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure", ["false", "raise", "partial", "empty", "incomplete", "noop", "interrupt"])
def test_promotion_failure_restores_destination(tmp_path, monkeypatch, existing, failure):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path)
    final, staging = "/output/final", "/staging"
    if existing:
        fs.local(final).mkdir(parents=True)
        (fs.local(final) / "old.csv").write_text("old complete data")
    rename = fs.rename
    files = {"part-00000.csv": "first", "part-00001.csv": "second", "_SUCCESS": ""}

    def fail_promotion(source, destination):
        if source.getName() != "staging":
            return rename(source, destination)
        if failure == "partial":
            fs.local(destination).mkdir()
            (fs.local(destination) / "partial.csv").write_text("partial")
        if failure in {"empty", "incomplete"}:
            rename(source, destination)
            (fs.local(destination) / "part-00000.csv").unlink()
            if failure == "empty":
                (fs.local(destination) / "part-00001.csv").unlink()
            return True
        if failure == "noop":
            return True
        if failure == "interrupt":
            raise KeyboardInterrupt()
        if failure == "false":
            return False
        raise OSError("promotion failed")

    monkeypatch.setattr(fs, "rename", fail_promotion)
    expected = KeyboardInterrupt if failure == "interrupt" else OSError
    with pytest.raises(expected):
        spark_utils.atomic_write_with_staging(
            dataframe(fs, HadoopWriter(fs, files)), final, staging,
        )

    if existing:
        assert [p.name for p in fs.local(final).iterdir()] == ["old.csv"]
        assert (fs.local(final) / "old.csv").read_text() == "old complete data"
    else:
        assert not fs.local(final).exists()
    assert not fs.local(staging).exists()
    assert not list(tmp_path.rglob("*_backup_*"))


@pytest.mark.parametrize("files", [{}, {"_SUCCESS": ""}, {"nested/_SUCCESS": ""}])
def test_empty_output_raises_without_touching_destination(tmp_path, monkeypatch, files):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path)
    final = fs.local("/final")
    final.mkdir()
    (final / "old.csv").write_text("old")
    logs = []
    monkeypatch.setattr(spark_utils, "log_info", logs.append)

    with pytest.raises(OSError, match="no data files"):
        spark_utils.atomic_write_with_staging(
            dataframe(fs, HadoopWriter(fs, files)), "/final", "/staging",
        )

    assert (final / "old.csv").read_text() == "old"
    assert fs.renames == []
    assert not fs.local("/staging").exists()
    assert not any("completed successfully" in line for line in logs)


@pytest.mark.parametrize("other_uri", ["s3a://bucket", "hdfs://other-namenode", "file://"])
def test_rejects_different_filesystems_before_writing(tmp_path, other_uri):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path / "hdfs")
    other = HadoopFileSystem(other_uri, tmp_path / "other")
    writer = HadoopWriter(fs)

    with pytest.raises(ValueError, match="same filesystem"):
        spark_utils.atomic_write_with_staging(
            dataframe(fs, writer, other), other_uri + "/final", "/staging",
        )

    assert writer.calls == []
    assert not list(tmp_path.iterdir())


def test_missing_jvm_raises_without_local_fallback(tmp_path):
    with pytest.raises(RuntimeError, match="JVM-backed"):
        spark_utils.atomic_write_with_staging(
            SimpleNamespace(), str(tmp_path / "final"), str(tmp_path / "staging"),
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("final,staging", [
    ("/same", "/same"), ("/final", "/final/staging"),
    ("/staging/final", "/staging"), ("/", "/staging"),
    ("hdfs://namenode/same", "/same"),
])
def test_rejects_overlapping_paths_before_cleanup(tmp_path, final, staging):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path)
    fs.local(staging).mkdir(parents=True)
    (fs.local(staging) / "sentinel").write_text("keep")
    writer = HadoopWriter(fs)

    with pytest.raises(ValueError, match="overlap"):
        spark_utils.atomic_write_with_staging(dataframe(fs, writer), final, staging)

    assert (fs.local(staging) / "sentinel").read_text() == "keep"
    assert writer.calls == []


@pytest.mark.parametrize("existing", ["absent", "empty", "nonempty", "file"])
def test_success_publishes_partitions_and_prunes_backup(tmp_path, existing):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path)
    final = fs.local("/final")
    if existing in {"empty", "nonempty"}:
        final.mkdir()
    if existing == "nonempty":
        (final / "old").write_text("old")
    if existing == "file":
        final.write_text("old")
    files = {"country=us/part-0.parquet": "new", "_SUCCESS": ""}

    spark_utils.atomic_write_with_staging(
        dataframe(fs, HadoopWriter(fs, files)), "/final", "/staging", file_format="parquet",
    )

    assert (final / "country=us/part-0.parquet").read_text() == "new"
    assert sorted(tmp_path.iterdir()) == [final]


def test_failed_restore_retains_backup_and_reports_location(tmp_path, monkeypatch):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path)
    fs.local("/final").mkdir()
    (fs.local("/final") / "old").write_text("recover me")
    rename = fs.rename

    def fail_after_backup(source, destination):
        if source.getName() == "final":
            return rename(source, destination)
        return False

    monkeypatch.setattr(fs, "rename", fail_after_backup)
    with pytest.raises(RuntimeError, match="backup.*final_backup_"):
        spark_utils.atomic_write_with_staging(dataframe(fs), "/final", "/staging")

    backups = list(tmp_path.glob("final_backup_*"))
    assert len(backups) == 1
    assert (backups[0] / "old").read_text() == "recover me"


@pytest.mark.parametrize("moved", [False, True])
def test_backup_rename_failure_preserves_old_data(tmp_path, monkeypatch, moved):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path)
    fs.local("/final").mkdir()
    (fs.local("/final") / "old").write_text("old")
    rename = fs.rename

    def fail_backup(source, destination):
        if source.getName() == "final":
            if moved:
                rename(source, destination)
            return False
        return rename(source, destination)

    monkeypatch.setattr(fs, "rename", fail_backup)
    with pytest.raises(OSError, match="rename"):
        spark_utils.atomic_write_with_staging(dataframe(fs), "/final", "/staging")

    assert (fs.local("/final") / "old").read_text() == "old"
    assert not fs.local("/staging").exists()


def test_cleanup_failure_does_not_mask_write_error(tmp_path, monkeypatch):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path)
    writer = HadoopWriter(fs)

    def fail_write(destination):
        fs.mkdirs(HadoopPath(destination))
        raise ValueError("write failed")

    monkeypatch.setattr(writer, "save", fail_write)
    monkeypatch.setattr(fs, "delete", lambda *args: False)
    with pytest.raises(ValueError, match="write failed"):
        spark_utils.atomic_write_with_staging(dataframe(fs, writer), "/final", "/staging")


def test_backup_pruning_failure_keeps_verified_output(tmp_path, monkeypatch):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path)
    fs.local("/final").mkdir()
    (fs.local("/final") / "old").write_text("old")
    delete = fs.delete

    def fail_pruning(path, recursive):
        if "_backup_" in path.getName():
            return False
        return delete(path, recursive)

    monkeypatch.setattr(fs, "delete", fail_pruning)
    with pytest.raises(OSError, match="Failed to delete.*backup_"):
        spark_utils.atomic_write_with_staging(dataframe(fs), "/final", "/staging")

    assert (fs.local("/final") / "part-00000.csv").read_text() == "id,name\n1,Ada\n"
    assert (next(tmp_path.glob("final_backup_*")) / "old").read_text() == "old"


@pytest.mark.parametrize("mode", ["overwrite", "append", "ignore", "errorifexists"])
def test_mode_applies_to_fresh_staging_and_final_is_replaced(tmp_path, mode):
    fs = HadoopFileSystem("hdfs://namenode", tmp_path)
    for name in ("/final", "/staging"):
        fs.local(name).mkdir()
        (fs.local(name) / "old").write_text("old")
    writer = HadoopWriter(fs)

    spark_utils.atomic_write_with_staging(dataframe(fs, writer), "/final", "/staging", mode=mode)

    assert not (fs.local("/final") / "old").exists()
    assert (fs.local("/final") / "part-00000.csv").read_text() == "id,name\n1,Ada\n"
    assert ("mode", mode) in writer.calls
