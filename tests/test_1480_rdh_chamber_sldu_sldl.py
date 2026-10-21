"""Regression tests for RDH enacted-plan chamber selection (#1480)."""

from unittest.mock import Mock, sentinel

import pytest

from siege_utilities.geo.providers.boundary_providers import RDHProvider
from siege_utilities.geo.providers.redistricting_data_hub import (
    RDHClient,
    RDHDataset,
    fetch_enacted_plan,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    with RDHClient(
        username="test-user", password="test-password", cache_dir=tmp_path,
    ) as client:
        monkeypatch.setattr(client, "list_datasets", Mock(return_value=[]))
        monkeypatch.setattr(client, "load_shapefile", Mock(return_value=sentinel.plan))
        yield client


def _dataset(title, *, official=False):
    return RDHDataset(
        title=title, url=f"https://example.test/{title}.zip", official=official,
    )


@pytest.mark.parametrize("chamber, code", [
    ("state_senate", "sldu"),
    ("state_house", "sldl"),
])
def test_census_chamber_codes(client, chamber, code):
    client.list_datasets.return_value = [
        _dataset("va_sldl_2021_adopted_plan"),
        _dataset("va_sldu_2021_adopted_plan"),
    ]

    plans = client.get_enacted_plans("VA", chamber=chamber, year="2021")

    assert [plan.title for plan in plans] == [f"va_{code}_2021_adopted_plan"]
    client.list_datasets.assert_called_once_with(
        states=["VA"], format="shp", year="2021",
    )


@pytest.mark.parametrize("chamber, keyword", [
    ("state_senate", "state senate"),
    ("state_senate", "upper"),
    ("state_senate", "senate"),
    ("state_senate", "sldu"),
    ("state_house", "state house"),
    ("state_house", "lower"),
    ("state_house", "house"),
    ("state_house", "sldl"),
    ("congress", "congressional"),
    ("congress", "congress"),
    ("congress", "cd"),
])
@pytest.mark.parametrize("separator", ["_", " ", "-"])
def test_chamber_keywords_match_whole_tokens(client, chamber, keyword, separator):
    title = separator.join(["VA", keyword.upper(), "2021", "ENACTED", "PLAN"])
    plan = _dataset(title)
    client.list_datasets.return_value = [plan]

    assert client.get_enacted_plans("VA", chamber=chamber.upper()) == [plan]


@pytest.mark.parametrize("chamber, word", [
    ("state_house", "household"),
    ("state_house", "houses"),
    ("state_house", "warehouse"),
    ("state_house", "lowering"),
    ("state_house", "flower"),
    ("state_senate", "uppermost"),
    ("state_senate", "supper"),
    ("congress", "abcde"),
])
def test_chamber_keywords_do_not_match_substrings(client, chamber, word):
    client.list_datasets.return_value = [_dataset(f"va_{word}_2021_adopted_plan")]

    assert client.get_enacted_plans("VA", chamber=chamber) == []


def test_chamber_match_still_requires_enacted_adopted_or_official(client):
    proposed = _dataset("va_house_2021_proposed_plan")
    official = _dataset("va_house_2021_plan", official=True)
    client.list_datasets.return_value = [proposed, official]

    assert client.get_enacted_plans("VA", chamber="state_house") == [official]


def _load_plan(client, entrypoint, chamber):
    if entrypoint == "fetch_enacted_plan":
        return fetch_enacted_plan("VA", chamber=chamber, year="2021", client=client)
    provider = RDHProvider()
    provider._client = client
    return provider.get_boundary(chamber, "VA", year="2021")


@pytest.mark.parametrize("entrypoint", ["fetch_enacted_plan", "get_boundary"])
@pytest.mark.parametrize("chamber, code", [
    ("state_senate", "sldu"),
    ("state_house", "sldl"),
])
def test_loaders_use_the_requested_chamber(client, entrypoint, chamber, code):
    plans = {
        code: _dataset(f"va_{code}_2021_adopted_plan")
        for code in ("sldl", "sldu")
    }
    client.list_datasets.return_value = list(plans.values())

    assert _load_plan(client, entrypoint, chamber) is sentinel.plan
    client.load_shapefile.assert_called_once_with(plans[code])


@pytest.mark.parametrize("entrypoint", [
    "get_enacted_plans", "fetch_enacted_plan", "get_boundary",
])
@pytest.mark.parametrize("chamber, keyword", [
    ("state_senate", "senate"),
    ("state_house", "house"),
    ("congress", "congress"),
])
@pytest.mark.parametrize("reverse", [False, True])
def test_ambiguous_chamber_is_refused_before_loading(
    client, entrypoint, chamber, keyword, reverse,
):
    plans = [
        _dataset(f"va_{keyword}_2021_adopted_plan_a"),
        _dataset(f"va_{keyword}_2021_adopted_plan_b"),
    ]
    client.list_datasets.return_value = plans[::-1] if reverse else plans

    with pytest.raises(ValueError, match="Ambiguous enacted") as exc:
        if entrypoint == "get_enacted_plans":
            client.get_enacted_plans("VA", chamber=chamber, year="2021")
        else:
            _load_plan(client, entrypoint, chamber)

    message = str(exc.value)
    for detail in ("VA", chamber, "2021", *(plan.title for plan in plans)):
        assert detail in message
    client.load_shapefile.assert_not_called()
