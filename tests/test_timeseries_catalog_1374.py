"""Yearless Census discovery regressions and year-based compatibility controls."""

import logging
from unittest.mock import Mock, call

import pytest
import requests

from siege_utilities.geo.census.catalog import CensusCatalogDataset
from siege_utilities.geo.census.catalog_populator import CensusCatalogPopulator


BASE_URL = "https://api.census.gov/data"
LOGGER = "siege_utilities.geo.census.catalog_populator"
TIMESERIES_CALLS = [
    call(f"{BASE_URL}/timeseries/eits/resconst/variables.json", timeout=30),
    call(f"{BASE_URL}/timeseries/eits/resconst/groups.json", timeout=30),
]


@pytest.fixture
def raw_variables():
    return {
        "time": {"label": "Time", "predicateType": "string"},
        "cell_value": {"label": "Value", "predicateType": "float"},
        "data_type_code": {
            "label": "Data type",
            "values": {"item": {"TOTAL": "Total"}},
        },
    }


@pytest.fixture
def responses(raw_variables):
    return [
        Mock(json=Mock(return_value={"variables": raw_variables})),
        Mock(json=Mock(return_value={"groups": []})),
    ]


@pytest.fixture(autouse=True)
def mock_get(monkeypatch, responses):
    request = Mock(side_effect=responses)
    monkeypatch.setattr(f"{LOGGER}.requests.get", request)
    return request


@pytest.mark.parametrize("dataset", ["eits/resconst", "timeseries/eits/resconst"])
def test_timeseries_exact_urls(dataset, mock_get, responses):
    CensusCatalogPopulator(base_url=BASE_URL).populate(dataset, year=None)

    assert mock_get.call_args_list == TIMESERIES_CALLS
    for response in responses:
        response.raise_for_status.assert_called_once_with()
        response.json.assert_called_once_with()


def test_unregistered_timeseries_path(mock_get):
    CensusCatalogPopulator(base_url=BASE_URL).populate("govs/schfin", year=None)

    assert mock_get.call_args_list == [
        call(f"{BASE_URL}/timeseries/govs/schfin/variables.json", timeout=30),
        call(f"{BASE_URL}/timeseries/govs/schfin/groups.json", timeout=30),
    ]


def test_omitted_year_selects_timeseries(mock_get):
    catalog = CensusCatalogPopulator(base_url=BASE_URL).populate("eits/resconst")

    assert mock_get.call_args_list == TIMESERIES_CALLS
    assert catalog.get_dataset("eits/resconst").year is None


@pytest.mark.parametrize("dataset", ["eits/resconst", "timeseries/eits/resconst"])
def test_timeseries_dataset_id_preserves_input(dataset):
    catalog = CensusCatalogPopulator().populate(dataset, year=None)

    assert list(catalog.datasets) == [dataset]
    ds = catalog.get_dataset(dataset)
    assert ds.dataset_id == dataset
    assert ds.year is None
    assert ds.survey_type == dataset


@pytest.mark.parametrize("groups", [[], [{"name": "series", "description": "Series metadata"}]])
def test_timeseries_retains_raw_metadata(raw_variables, responses, groups):
    responses[1].json.return_value = {"groups": groups}
    catalog = CensusCatalogPopulator().populate(
        "eits/resconst", year=None, survey_type="economic_indicators",
    )
    ds = next(iter(catalog.datasets.values()))

    assert ds.timeseries_variables == raw_variables
    assert ds.timeseries_groups == groups
    assert ds.survey_type == "economic_indicators"
    assert ds.tables == {}
    assert ds.subjects == []
    assert catalog.tables == {}
    assert catalog.families == {}
    assert catalog.subjects == {}


def test_timeseries_logs_raw_variable_count(caplog):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        CensusCatalogPopulator().populate("eits/resconst", year=None)

    messages = [
        record.getMessage() for record in caplog.records
        if record.name == LOGGER and record.levelno == logging.INFO
    ]
    assert len(messages) == 1
    assert "ACS-style table/family grouping does not apply to timeseries" in messages[0]
    assert "3 raw variables" in messages[0]


def test_dataset_defaults_to_yearless():
    ds = CensusCatalogDataset(dataset_id="eits/resconst", survey_type="eits")

    assert ds.year is None
    assert ds.timeseries_variables is None
    assert ds.timeseries_groups is None


def test_year_based_exact_urls_unchanged(mock_get):
    CensusCatalogPopulator(base_url=BASE_URL).populate("acs5", 2023)

    assert mock_get.call_args_list == [
        call(f"{BASE_URL}/2023/acs/acs5/variables.json", timeout=30),
        call(f"{BASE_URL}/2023/acs/acs5/groups.json", timeout=30),
    ]


def test_year_based_dataset_id_unchanged():
    catalog = CensusCatalogPopulator().populate("acs5", 2023)

    assert list(catalog.datasets) == ["acs5_2023"]
    ds = catalog.get_dataset("acs5_2023")
    assert ds.dataset_id == "acs5_2023"
    assert ds.year == 2023


def test_year_based_metadata_and_logging(responses, caplog):
    responses[0].json.return_value = {
        "variables": {
            "B01001_001E": {"label": "Estimate!!Total:", "concept": "SEX BY AGE"},
        },
    }
    responses[1].json.return_value = {
        "groups": [{"name": "B01001", "description": "Age-Sex--SEX BY AGE"}],
    }
    with caplog.at_level(logging.INFO, logger=LOGGER):
        catalog = CensusCatalogPopulator().populate("acs5", 2023)
    ds = catalog.get_dataset("acs5_2023")

    assert ds.timeseries_variables is None
    assert ds.timeseries_groups is None
    assert list(ds.tables) == ["B01001"]
    assert ds.subjects[0].subject_id == "age-sex"
    assert "Populated catalog for acs5/2023: 1 tables, 0 families, 1 subjects" in caplog.text
    assert "does not apply to timeseries" not in caplog.text


@pytest.mark.parametrize("status", [404, 503])
@pytest.mark.parametrize("endpoint", ["variables", "groups"])
def test_timeseries_http_error_propagates(endpoint, status, mock_get, responses):
    response_index = 0 if endpoint == "variables" else 1
    failed_response = responses[response_index]
    failed_response.status_code = status
    error = requests.HTTPError(f"HTTP {status}", response=failed_response)
    failed_response.raise_for_status.side_effect = error

    with pytest.raises(requests.HTTPError) as caught:
        CensusCatalogPopulator(base_url=BASE_URL).populate("eits/resconst", year=None)

    assert caught.value is error
    failed_response.raise_for_status.assert_called_once_with()
    failed_response.json.assert_not_called()
    assert mock_get.call_args_list == TIMESERIES_CALLS[:response_index + 1]


def test_timeseries_metadata_survives_cache_roundtrip():
    """#1374 P2: the disk-cache (de)serializer must retain a timeseries
    dataset's raw variables/groups; dropping them silently loses data (SU-1).
    """
    from siege_utilities.geo.census.catalog import CensusCatalog
    from siege_utilities.geo.census.catalog_cache import (
        _catalog_from_dict,
        _catalog_to_dict,
    )

    catalog = CensusCatalog()
    catalog.add_dataset(
        CensusCatalogDataset(
            dataset_id="eits/resconst",
            survey_type="eits/resconst",
            year=None,
            timeseries_variables={"cell_value": {"label": "Value"}, "time": {}},
            timeseries_groups=[{"name": "g1"}],
        )
    )

    restored = _catalog_from_dict(_catalog_to_dict(catalog))
    ds = restored.datasets["eits/resconst"]
    assert ds.year is None
    assert ds.timeseries_variables == {"cell_value": {"label": "Value"}, "time": {}}
    assert ds.timeseries_groups == [{"name": "g1"}]


def test_year_based_dataset_has_no_timeseries_metadata_after_roundtrip():
    """A year-based dataset keeps the timeseries fields None across the cache."""
    from siege_utilities.geo.census.catalog import CensusCatalog
    from siege_utilities.geo.census.catalog_cache import (
        _catalog_from_dict,
        _catalog_to_dict,
    )

    catalog = CensusCatalog()
    catalog.add_dataset(
        CensusCatalogDataset(dataset_id="acs5_2023", survey_type="acs5", year=2023)
    )

    restored = _catalog_from_dict(_catalog_to_dict(catalog))
    ds = restored.datasets["acs5_2023"]
    assert ds.year == 2023
    assert ds.timeseries_variables is None
    assert ds.timeseries_groups is None
