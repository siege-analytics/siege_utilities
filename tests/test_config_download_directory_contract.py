"""Canonical contract test for root get_download_directory export."""

from siege_utilities import get_download_directory


def test_get_download_directory_specific_path_wins_from_root_import(tmp_path):
    target = tmp_path / "parent" / "downloads"

    result = get_download_directory(specific_path=str(target))

    assert result == target
    assert target.is_dir()
