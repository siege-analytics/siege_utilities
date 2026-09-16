"""Canonical root-import contracts for distributed write helpers."""

from pathlib import Path
from unittest.mock import Mock

from siege_utilities.distributed import atomic_write_with_staging
from siege_utilities.distributed import export_prepared_df_as_csv_to_path_using_delimiter  # noqa: E501


class SavingWriter:
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
        Path(destination).mkdir(parents=True, exist_ok=True)
        Path(destination, "part-00000.csv").write_text("id,name\n1,Ada\n")


def test_atomic_write_with_staging_moves_files_and_cleans_staging(tmp_path):
    writer = SavingWriter()
    df = Mock()
    df.write = writer
    final_destination = tmp_path / "final"
    staging_directory = tmp_path / "staging"

    atomic_write_with_staging(
        df,
        str(final_destination),
        str(staging_directory),
        delimiter="|",
        header=False,
    )

    assert (
        final_destination / "part-00000.csv"
    ).read_text() == "id,name\n1,Ada\n"
    assert not staging_directory.exists()
    assert ("mode", "overwrite") in writer.calls
    assert ("format", "csv") in writer.calls
    assert ("option", "header", "false") in writer.calls
    assert ("option", "delimiter", "|") in writer.calls
    assert ("save", str(staging_directory)) in writer.calls


def test_export_prepared_df_as_csv_uses_prepared_frame_and_delimiter(
    monkeypatch,
    tmp_path,
):
    from siege_utilities.distributed import spark_utils

    original_df = Mock()
    prepared_df = Mock()
    coalesced = Mock()
    writer = Mock()
    prepared_df.coalesce.return_value = coalesced
    coalesced.write = writer
    writer.format.return_value = writer
    writer.option.return_value = writer
    writer.mode.return_value = writer
    output_path = tmp_path / "exports" / "step_one"

    monkeypatch.setattr(
        spark_utils,
        "prepare_dataframe_for_export",
        lambda df: prepared_df,
    )

    export_prepared_df_as_csv_to_path_using_delimiter(
        original_df,
        output_path,
        delimiter="\t",
    )

    prepared_df.coalesce.assert_called_once_with(1)
    writer.format.assert_called_once_with("csv")
    writer.option.assert_any_call("header", "true")
    writer.option.assert_any_call("delimiter", "\t")
    writer.mode.assert_called_once_with("overwrite")
    writer.save.assert_called_once_with(str(output_path))
