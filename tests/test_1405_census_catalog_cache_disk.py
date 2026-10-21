"""Disk-cache regressions for Census dataset ids containing slashes (#1405)."""

import json
import logging
import os
from unittest.mock import Mock

import pytest

from siege_utilities.geo.census.catalog import (
    CensusCatalog,
    CensusCatalogDataset,
)
from siege_utilities.geo.census.catalog_cache import (
    CatalogCache,
    CatalogLoader,
)


LOGGER = "siege_utilities.geo.census.catalog_cache"


@pytest.mark.parametrize(
    ("dataset", "year"),
    [
        ("eits/resconst", None),
        ("timeseries/eits/resconst", None),
        ("dec/pl", 2020),
    ],
)
def test_catalog_survives_disk_round_trip(
    tmp_path, monkeypatch, dataset, year,
):
    variables = {
        "time": {"label": "Time", "predicateType": "string"},
        "cell_value": {"label": "Value", "predicateType": "float"},
    }
    groups = [{"name": "series", "description": "Series metadata"}]
    request = Mock(side_effect=[
        Mock(json=Mock(return_value={"variables": variables})),
        Mock(json=Mock(return_value={"groups": groups})),
    ])
    monkeypatch.setattr(
        "siege_utilities.geo.census.catalog_populator.requests.get", request,
    )
    cache_dir = tmp_path / "catalog"
    cache = CatalogCache(cache_dir=cache_dir)
    original = CatalogLoader(cache=cache).load(dataset, year)

    entries = list(cache_dir.rglob("*.json"))
    assert len(entries) == 1, "The catalog must produce a readable disk entry"
    payload = json.loads(entries[0].read_text(encoding="utf-8"))
    assert payload["datasets"][0]["year"] == year

    # A fresh loader/cache must read from disk without another API request.
    reader = CatalogLoader(cache=CatalogCache(cache_dir=cache_dir))
    restored = reader.load(dataset, year)
    assert restored is not original
    assert request.call_count == 2
    dataset_id = dataset if year is None else f"{dataset}_{year}"
    restored_dataset = restored.get_dataset(dataset_id)
    assert restored_dataset is not None
    assert restored_dataset.year == year
    expected_variables = variables if year is None else None
    expected_groups = groups if year is None else None
    assert restored_dataset.timeseries_variables == expected_variables
    assert restored_dataset.timeseries_groups == expected_groups

    # Every entry must also remain discoverable by cache invalidation.
    assert cache.clear() == 1
    assert not entries[0].exists()


def test_cache_keys_stay_separate_and_inside_cache_directory(tmp_path):
    cache_dir = tmp_path / "catalog"
    cache = CatalogCache(cache_dir=cache_dir)
    keys = [
        ("eits/resconst", None),
        ("eits/resconst", 2020),
        ("eits%2Fresconst", None),
        ("eits_resconst", None),
        ("../eits/resconst", None),
        ("eits\\resconst:?*\x00", None),
    ]
    for dataset, year in keys:
        catalog = CensusCatalog()
        catalog.add_dataset(CensusCatalogDataset(
            dataset_id=dataset, survey_type=dataset, year=year,
        ))
        cache.put(dataset, year, catalog)

    # Reading the JSON proves that each key produced a real, distinct file.
    entries = list(cache_dir.glob("*.json"))
    assert len(entries) == len(keys)
    for path in entries:
        assert json.loads(path.read_text(encoding="utf-8"))
    reader = CatalogCache(cache_dir=cache_dir)
    for dataset, year in keys:
        restored = reader.get(dataset, year)
        assert restored is not None
        assert list(restored.datasets) == [dataset]
        assert restored.get_dataset(dataset).year == year
    assert len(list(tmp_path.rglob("*.json"))) == len(keys)
    assert cache.clear() == len(keys)


def test_yearless_write_failure_logs_warning(tmp_path, caplog):
    cache = CatalogCache(cache_dir=tmp_path)
    # A directory at the destination causes a real atomic-replace failure.
    path = cache._cache_path("eits/resconst", None)
    path.mkdir(parents=True)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        cache.put("eits/resconst", None, CensusCatalog())

    assert path.is_dir()
    assert "Failed to cache catalog for eits/resconst/None:" in caplog.text


@pytest.mark.parametrize("entry_state", ["valid", "expired", "corrupt"])
def test_yearless_cache_logging(tmp_path, caplog, entry_state):
    cache = CatalogCache(cache_dir=tmp_path)
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        cache.put("eits/resconst", None, CensusCatalog())
        path = cache._cache_path("eits/resconst", None)
        if entry_state == "expired":
            os.utime(path, (0, 0))
        elif entry_state == "corrupt":
            path.write_text("not json", encoding="utf-8")
        restored = cache.get("eits/resconst", None)

    assert "Cached catalog for eits/resconst/None" in caplog.text
    if entry_state == "valid":
        assert restored is not None
        assert "Cache hit for eits/resconst/None" in caplog.text
    elif entry_state == "expired":
        assert restored is None
        assert not path.exists()
        assert "Cache expired for eits/resconst/None" in caplog.text
    else:
        assert restored is None
        assert "Failed to read cache for eits/resconst/None" in caplog.text
