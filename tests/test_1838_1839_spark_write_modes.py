"""Regression tests for non-destructive Spark write defaults (#1838, #1839).

``write_df_to_parquet`` (#1838) and
``export_prepared_df_as_csv_to_path_using_delimiter`` (#1839) used to replace
an existing destination by default; the CSV export offered no way to opt out.
Both now default to Spark's ``errorifexists`` mode and accept an explicit
``mode`` for callers that want to overwrite, append or ignore.

Fake-writer tests record the mode each helper passes to Spark. Real-Spark
tests (skipped when pyspark is unavailable) prove an existing destination
survives a default write and is replaced only on explicit opt-in.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from siege_utilities.distributed import spark_utils
from siege_utilities.distributed.spark_utils import (
    export_prepared_df_as_csv_to_path_using_delimiter,
    write_df_to_parquet,
)


class RecordingWriter:
    """Fake ``DataFrameWriter`` that records the chain it is driven through."""

    def __init__(self):
        self.calls = []

    def mode(self, value):
        self.calls.append(("mode", value))
        return self

    def format(self, value):
        self.calls.append(("format", value))
        return self

    def option(self, key, value):
        self.calls.append(("option", key, value))
        return self

    def save(self, destination):
        self.calls.append(("save", destination))

    def parquet(self, destination):
        self.calls.append(("parquet", destination))

    def modes(self):
        return [call[1] for call in self.calls if call[0] == "mode"]

    def wrote(self):
        return any(call[0] in ("save", "parquet") for call in self.calls)


def _fake_df():
    df = Mock()
    df.write = RecordingWriter()
    return df


@pytest.fixture
def export_writer(monkeypatch):
    """Route the CSV export through a recording writer."""
    prepared = Mock()
    writer = RecordingWriter()
    prepared.coalesce.return_value.write = writer
    monkeypatch.setattr(spark_utils, "prepare_dataframe_for_export", lambda df: prepared)
    return writer


# --- #1838: write_df_to_parquet ------------------------------------------------


def test_parquet_default_mode_is_not_overwrite():
    df = _fake_df()

    write_df_to_parquet(df, "/out/path")

    assert df.write.modes() == ["errorifexists"]
    assert ("parquet", "/out/path") in df.write.calls


@pytest.mark.parametrize("mode", ["overwrite", "append", "ignore", "error", "errorifexists"])
def test_parquet_explicit_mode_is_passed_through(mode):
    df = _fake_df()

    write_df_to_parquet(df, "/out/path", mode=mode)

    assert df.write.modes() == [mode]


@pytest.mark.parametrize(("mode", "expected"), [("Overwrite", "overwrite"), ("ERROR", "error")])
def test_parquet_mode_is_case_insensitive_like_spark(mode, expected):
    df = _fake_df()

    write_df_to_parquet(df, "/out/path", mode=mode)

    assert df.write.modes() == [expected]


@pytest.mark.parametrize("mode", ["replace", "default", "", None, 1])
def test_parquet_invalid_mode_raises_before_write(mode):
    df = _fake_df()

    with pytest.raises(ValueError, match="Invalid Spark write mode"):
        write_df_to_parquet(df, "/out/path", mode=mode)

    assert not df.write.wrote()


# --- #1839: export_prepared_df_as_csv_to_path_using_delimiter -------------------


def test_csv_export_default_mode_is_not_overwrite(export_writer, tmp_path):
    export_prepared_df_as_csv_to_path_using_delimiter(Mock(), tmp_path / "step")

    assert export_writer.modes() == ["errorifexists"]


@pytest.mark.parametrize("mode", ["overwrite", "append", "ignore", "error", "errorifexists"])
def test_csv_export_caller_controls_mode(export_writer, tmp_path, mode):
    export_prepared_df_as_csv_to_path_using_delimiter(
        Mock(), tmp_path / "step", delimiter="|", mode=mode
    )

    assert export_writer.modes() == [mode]
    assert ("option", "delimiter", "|") in export_writer.calls
    assert ("save", str(tmp_path / "step")) in export_writer.calls


def test_csv_export_mode_is_case_insensitive_like_spark(export_writer, tmp_path):
    export_prepared_df_as_csv_to_path_using_delimiter(
        Mock(), tmp_path / "step", mode="OVERWRITE"
    )

    assert export_writer.modes() == ["overwrite"]


@pytest.mark.parametrize("mode", ["truncate", "", None])
def test_csv_export_invalid_mode_raises_before_prepare_or_write(monkeypatch, tmp_path, mode):
    prepare = Mock()
    monkeypatch.setattr(spark_utils, "prepare_dataframe_for_export", prepare)

    with pytest.raises(ValueError, match="Invalid Spark write mode"):
        export_prepared_df_as_csv_to_path_using_delimiter(
            Mock(), tmp_path / "step", mode=mode
        )

    prepare.assert_not_called()


# --- 'ignore' must not claim a write it cannot confirm -------------------------


def test_parquet_ignore_mode_does_not_log_a_write(caplog):
    with caplog.at_level("INFO"):
        write_df_to_parquet(_fake_df(), "/out/path", mode="ignore")

    assert "Dataframe written" not in caplog.text
    assert "nothing was written if the path already existed" in caplog.text


def test_csv_export_ignore_mode_does_not_log_success(export_writer, tmp_path, caplog):
    with caplog.at_level("INFO"):
        export_prepared_df_as_csv_to_path_using_delimiter(
            Mock(), tmp_path / "step", mode="ignore"
        )

    assert "successfully exported" not in caplog.text
    assert "nothing was written if the path already existed" in caplog.text


@pytest.mark.parametrize("mode", ["overwrite", "errorifexists"])
def test_non_ignore_modes_keep_the_write_log(mode, caplog):
    with caplog.at_level("INFO"):
        write_df_to_parquet(_fake_df(), "/out/path", mode=mode)

    assert f"Dataframe written to parquet at /out/path with mode '{mode}'" in caplog.text


# --- Real Spark: existing destinations survive a default write ----------------


def _sentinel_dir(path: Path) -> Path:
    path.mkdir(parents=True)
    sentinel = path / "caller_sentinel.txt"
    sentinel.write_text("keep me")
    return sentinel


def _analysis_exception():
    """Spark's AnalysisException; ``pyspark.errors`` only exists from 3.4."""
    try:
        from pyspark.errors import AnalysisException
    except ImportError:  # pyspark 3.3, the declared floor
        from pyspark.sql.utils import AnalysisException
    return AnalysisException


@pytest.mark.e2e
def test_parquet_default_write_preserves_existing_destination(real_spark_session, tmp_path):
    AnalysisException = _analysis_exception()

    destination = tmp_path / "pq"
    sentinel = _sentinel_dir(destination)
    df = real_spark_session.createDataFrame([(1, "a")], ["id", "name"])

    with pytest.raises(AnalysisException):
        write_df_to_parquet(df, str(destination))

    assert sentinel.read_text() == "keep me"


@pytest.mark.e2e
def test_parquet_explicit_overwrite_replaces_destination(real_spark_session, tmp_path):
    destination = tmp_path / "pq"
    sentinel = _sentinel_dir(destination)
    df = real_spark_session.createDataFrame([(1, "a")], ["id", "name"])

    write_df_to_parquet(df, str(destination), mode="overwrite")

    assert not sentinel.exists()
    assert real_spark_session.read.parquet(str(destination)).count() == 1


@pytest.mark.e2e
def test_csv_export_default_preserves_existing_destination(real_spark_session, tmp_path):
    AnalysisException = _analysis_exception()

    destination = tmp_path / "csv_out"
    sentinel = _sentinel_dir(destination)
    df = real_spark_session.createDataFrame([(1, "a")], ["id", "name"])

    with pytest.raises(AnalysisException):
        export_prepared_df_as_csv_to_path_using_delimiter(df, destination)

    assert sentinel.read_text() == "keep me"


@pytest.mark.e2e
def test_csv_export_explicit_overwrite_replaces_destination(real_spark_session, tmp_path):
    destination = tmp_path / "csv_out"
    sentinel = _sentinel_dir(destination)
    df = real_spark_session.createDataFrame([(1, "a")], ["id", "name"])

    export_prepared_df_as_csv_to_path_using_delimiter(df, destination, mode="overwrite")

    assert not sentinel.exists()
    back = real_spark_session.read.option("header", "true").csv(str(destination))
    assert back.count() == 1


@pytest.mark.e2e
def test_csv_export_ignore_mode_leaves_destination_untouched(real_spark_session, tmp_path):
    destination = tmp_path / "csv_out"
    sentinel = _sentinel_dir(destination)
    df = real_spark_session.createDataFrame([(1, "a")], ["id", "name"])

    export_prepared_df_as_csv_to_path_using_delimiter(df, destination, mode="ignore")

    assert sentinel.read_text() == "keep me"
    assert sorted(p.name for p in destination.iterdir()) == ["caller_sentinel.txt"]
