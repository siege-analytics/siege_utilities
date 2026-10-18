"""Offline regressions for metric/day parsing and connector API isolation."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest


@pytest.fixture
def sdk(monkeypatch):
    from siege_utilities.analytics import facebook_business as mod

    class FakeApi:
        """Model the SDK's default API so implicit token sharing is visible."""

        def __init__(self, session):
            self.session = session

        @classmethod
        def init(cls, app_id=None, app_secret=None, access_token=None):
            cls.default_api = cls(SimpleNamespace(access_token=access_token))
            return cls.default_api

        @classmethod
        def get_default_api(cls):
            return cls.default_api

    FakeApi.init(access_token="preexisting-token")
    original_api = FakeApi.get_default_api()
    objects = []

    def make_object(fbid=None, api=None):
        obj = MagicMock()
        obj.api = api if api is not None else FakeApi.get_default_api()
        obj.get_insights.return_value = iter(())
        obj.get_ad_accounts.return_value = iter(())
        objects.append(obj)
        return obj

    factories = {name: MagicMock(side_effect=make_object)
                 for name in ("Page", "AdAccount", "Business", "User")}
    monkeypatch.setattr(mod, "FACEBOOK_BUSINESS_AVAILABLE", True)
    monkeypatch.setattr(mod, "FacebookAdsApi", FakeApi, raising=False)
    monkeypatch.setattr(
        mod, "FacebookSession", SimpleNamespace, raising=False,
    )
    for name in ("Page", "AdAccount", "Business"):
        monkeypatch.setattr(mod, name, factories[name], raising=False)
    monkeypatch.setattr(
        mod, "facebook_business",
        SimpleNamespace(adobjects=SimpleNamespace(
            user=SimpleNamespace(User=factories["User"]),
        )),
        raising=False,
    )
    return SimpleNamespace(
        module=mod, api=FakeApi, original_api=original_api,
        factories=factories, objects=objects,
    )


@pytest.fixture
def page_insights(sdk):
    """Supply a one-pass SDK cursor without making network requests."""
    connector = sdk.module.FacebookBusinessConnector("page-token")

    def retrieve(insights, metrics):
        page = MagicMock()
        page.get_insights.return_value = iter(insights)
        sdk.factories["Page"].side_effect = None
        sdk.factories["Page"].return_value = page
        return connector.get_page_insights(
            "page-123", "2024-01-01", "2024-01-02", metrics=metrics,
        )

    return retrieve


def test_page_insights_pivots_each_metric_for_each_day(page_insights):
    df = page_insights([
        {"name": "page_impressions", "values": [
            {"end_time": "2024-01-01", "value": 10},
            {"end_time": "2024-01-02", "value": 20},
        ]},
        {"name": "page_fans", "values": [
            {"end_time": "2024-01-01", "value": 100},
            {"end_time": "2024-01-02", "value": 110},
        ]},
    ], ["page_impressions", "page_fans"])

    assert len(df) == 2
    assert df["page_impressions"].tolist() == [10, 20]
    assert df["page_fans"].tolist() == [100, 110]
    assert df["date"].is_unique


def test_page_insights_keeps_every_end_time_verbatim(page_insights):
    dates = ["2024-01-01T08:00:00+0000", "2024-01-02T08:00:00+0000"]
    df = page_insights([
        {"name": "page_impressions", "values": [
            {"end_time": dates[0], "value": 10},
            {"end_time": dates[1], "value": 20},
        ]},
    ], ["page_impressions"])

    assert df["date"].tolist() == dates


@pytest.mark.parametrize("empty_insight", [
    {"name": "page_fans", "values": []},
    {"name": "page_fans", "values": None},
    {"name": "page_fans"},
], ids=["empty", "null", "missing"])
def test_page_insights_keeps_empty_metrics_on_real_days(
    page_insights, empty_insight,
):
    df = page_insights([
        {"name": "page_impressions", "values": [
            {"end_time": "2024-01-01", "value": 10},
            {"end_time": "2024-01-02", "value": 20},
        ]},
        empty_insight,
    ], ["page_impressions", "page_fans"])

    assert df["date"].tolist() == ["2024-01-01", "2024-01-02"]
    assert df["page_impressions"].tolist() == [10, 20]
    assert (df["page_fans"].isna() | df["page_fans"].eq(0)).all()


def test_page_insights_joins_sparse_metrics_by_date(page_insights):
    df = page_insights([
        {"name": "page_impressions", "values": [
            {"end_time": "2024-01-01", "value": 10},
            {"end_time": "2024-01-02"},
        ]},
        {"name": "page_fans", "values": [
            {"end_time": "2024-01-03", "value": 120},
            {"end_time": "2024-01-01", "value": 100},
        ]},
    ], ["page_impressions", "page_fans"]).set_index("date")

    assert set(df.index) == {"2024-01-01", "2024-01-02", "2024-01-03"}
    assert df.loc["2024-01-01"].tolist() == [10, 100]
    assert df.loc["2024-01-03", "page_fans"] == 120
    for date, metric in [
        ("2024-01-02", "page_impressions"),
        ("2024-01-02", "page_fans"),
        ("2024-01-03", "page_impressions"),
    ]:
        value = df.loc[date, metric]
        assert pd.isna(value) or value == 0


@pytest.mark.parametrize("insights", [
    [],
    [{"name": "page_impressions", "values": []}],
    [{"values": [{"end_time": "2024-01-01", "value": 999}]}],
], ids=["no-insights", "no-values", "no-name"])
def test_page_insights_without_named_values_has_schema(page_insights, insights):
    df = page_insights(insights, ["page_impressions", "page_fans"])

    assert df.empty
    assert df.columns.tolist() == ["date", "page_impressions", "page_fans"]


@pytest.mark.parametrize("method, factory_name, args", [
    ("get_page_insights", "Page", ("page-123", "2024-01-01", "2024-01-02")),
    ("get_ad_insights", "AdAccount", ("act-123", "2024-01-01", "2024-01-02")),
    ("get_business_insights", "Business", ("biz-123", "2024-01-01", "2024-01-02")),
    ("get_ad_accounts", "User", ()),
])
def test_sdk_calls_use_each_connectors_token(sdk, method, factory_name, args):
    first = sdk.module.FacebookBusinessConnector("first-token")
    second = sdk.module.FacebookBusinessConnector("second-token")

    # Interleave calls after both connectors exist to catch last-init wins.
    for connector, token in [
        (first, "first-token"), (second, "second-token"), (first, "first-token"),
    ]:
        getattr(connector, method)(*args)
        assert sdk.objects[-1].api.session.access_token == token
        assert sdk.factories[factory_name].call_args.kwargs["api"] is connector.api

    assert first.api is not second.api


def test_connector_preserves_preexisting_default_api(sdk):
    sdk.module.FacebookBusinessConnector("first-token")
    sdk.module.FacebookBusinessConnector("second-token")

    assert sdk.api.get_default_api() is sdk.original_api
