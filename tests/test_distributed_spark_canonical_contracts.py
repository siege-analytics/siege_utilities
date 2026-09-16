"""Canonical root-import contracts for distributed Spark helper functions."""

from unittest.mock import Mock

import pytest

from siege_utilities.distributed import backup_full_dataframe
from siege_utilities.distributed import print_debug_table
from siege_utilities.distributed import reproject_geom_columns


def test_reproject_geom_columns_rejects_invalid_source_srid():
    with pytest.raises(ValueError, match="Invalid source_srid"):
        reproject_geom_columns(Mock(), ["geom"], "not-an-epsg", "EPSG:3857")


def test_reproject_geom_columns_rejects_invalid_target_srid():
    with pytest.raises(ValueError, match="Invalid target_srid"):
        reproject_geom_columns(Mock(), ["geom"], "EPSG:4326", "bad-target")


def test_print_debug_table_requires_tabulate(monkeypatch):
    from siege_utilities.distributed import spark_utils

    monkeypatch.setattr(spark_utils, "tabulate", None)

    with pytest.raises(ImportError, match="pip install tabulate"):
        print_debug_table(Mock(), "debug-title")


def test_backup_full_dataframe_writes_debug_snapshot(monkeypatch, tmp_path):
    from siege_utilities.distributed import spark_utils

    writer = Mock()
    writer.format.return_value = writer
    writer.option.return_value = writer
    df = Mock()
    df.write = writer
    monkeypatch.setattr(spark_utils, "DEBUG_SUBDIRECTORY", tmp_path)

    backup_full_dataframe(df, "stage_one")

    writer.format.assert_called_once_with("csv")
    writer.option.assert_any_call("header", "true")
    writer.option.assert_any_call("delimiter", ",")
    writer.save.assert_called_once_with(
        str(tmp_path / "stage_one_full_persisted"),
    )
