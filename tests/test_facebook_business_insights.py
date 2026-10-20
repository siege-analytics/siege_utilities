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


@pytest.mark.parametrize("dates, measured_days", [
    (["2024-01-01T08:00:00+0000", "2024-01-02T08:00:00+0000"],
     ["2023-12-31", "2024-01-01"]),
    (["2024-03-01T00:00:00+1400", "2024-03-02T00:00:00+1400"],
     ["2024-02-29", "2024-03-01"]),
])
def test_page_insights_normalises_every_end_time_to_measured_day(
    page_insights, dates, measured_days,
):
    df = page_insights([
        {"name": "page_impressions", "values": [
            {"end_time": dates[0], "value": 10},
            {"end_time": dates[1], "value": 20},
        ]},
    ], ["page_impressions"])

    assert df["date"].tolist() == measured_days


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

    assert df["date"].tolist() == ["2023-12-31", "2024-01-01"]
    assert df["page_impressions"].tolist() == [10, 20]
    assert df["page_fans"].isna().all()


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

    assert set(df.index) == {"2023-12-31", "2024-01-01", "2024-01-02"}
    assert df.loc["2023-12-31"].tolist() == [10, 100]
    assert df.loc["2024-01-02", "page_fans"] == 120
    for date, metric in [
        ("2024-01-01", "page_impressions"),
        ("2024-01-01", "page_fans"),
        ("2024-01-02", "page_impressions"),
    ]:
        value = df.loc[date, metric]
        assert pd.isna(value)


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


def test_page_insights_preserves_zero_values(page_insights):
    df = page_insights([
        {"name": "page_impressions", "values": [
            {"end_time": "2024-01-02T08:00:00+0000", "value": 0},
            {"end_time": "2024-01-03T08:00:00+0000"},
        ]},
    ], ["page_impressions"])

    assert df["page_impressions"].iloc[0] == 0
    assert pd.isna(df["page_impressions"].iloc[1])


def test_ad_insights_custom_fields_keep_identifiers_without_mutating_input(sdk):
    connector = sdk.module.FacebookBusinessConnector("tok")
    account = MagicMock()
    account.get_insights.return_value = iter([
        {"ad_id": "1", "ad_name": "A", "date_start": "2024-01-01",
         "date_stop": "2024-01-01", "clicks": 0},
        {"ad_id": "1", "ad_name": "A", "date_start": "2024-01-02",
         "date_stop": "2024-01-02"},
    ])
    sdk.factories["AdAccount"].side_effect = None
    sdk.factories["AdAccount"].return_value = account
    fields = ["clicks", "ad_id"]

    df = connector.get_ad_insights(
        "act_1", "2024-01-01", "2024-01-02", fields=fields,
    )

    assert fields == ["clicks", "ad_id"]
    assert df.columns.tolist() == [
        "clicks", "ad_id", "ad_name", "date_start", "date_stop",
    ]
    assert account.get_insights.call_args.kwargs["fields"] == df.columns.tolist()
    assert df["ad_id"].tolist() == ["1", "1"]
    assert df["ad_name"].tolist() == ["A", "A"]
    assert df["date_start"].tolist() == ["2024-01-01", "2024-01-02"]
    assert df["date_stop"].tolist() == ["2024-01-01", "2024-01-02"]
    assert df.loc[0, "clicks"] == 0
    assert pd.isna(df.loc[1, "clicks"])


def test_business_insights_distinguishes_absent_metrics_from_zero(sdk):
    connector = sdk.module.FacebookBusinessConnector("tok")
    business = MagicMock()
    business.get_insights.return_value = iter([{"clicks": 0}, {}])
    sdk.factories["Business"].side_effect = None
    sdk.factories["Business"].return_value = business

    df = connector.get_business_insights("biz_1", "2024-01-01", "2024-01-02")

    assert df.loc[0, "clicks"] == 0
    assert pd.isna(df.loc[1, "clicks"])
    assert df["impressions"].isna().all()


@pytest.mark.parametrize("account_type, method", [
    ("ad_account", "get_ad_insights"),
    ("page", "get_page_insights"),
    ("business", "get_business_insights"),
])
def test_batch_uses_config_directory_for_each_account_type(
    sdk, monkeypatch, tmp_path, account_type, method,
):
    config_directory = str(tmp_path / "config")
    profile = sdk.module.create_facebook_account_profile(
        "client-123", "account-123", account_type=account_type,
        access_token="custom-profile-token",
    )
    sdk.module.save_facebook_account_profile(
        profile, config_directory=config_directory,
    )
    connector = MagicMock()
    frame = pd.DataFrame({"impressions": [10]})
    getattr(connector, method).return_value = frame
    factory = MagicMock(return_value=connector)
    monkeypatch.setattr(sdk.module, "FacebookBusinessConnector", factory)
    output_directory = tmp_path / "output"

    result = sdk.module.batch_retrieve_facebook_data(
        "client-123", "2024-01-01", "2024-01-02", data_types=[account_type],
        output_directory=str(output_directory), config_directory=config_directory,
    )

    assert result["success"] is True
    assert result["errors"] == []
    assert result["accounts_processed"] == 1
    assert result["total_rows"] == 1
    factory.assert_called_once_with("custom-profile-token")
    getattr(connector, method).assert_called_once_with(
        "account-123", "2024-01-01", "2024-01-02",
    )
    output_file = str(output_directory / "fb_account-123_2024-01-01_2024-01-02.parquet")
    connector.save_as_pandas.assert_called_once_with(frame, output_file, "parquet")
    assert result["output_files"] == [output_file]


import inspect


def test_page_insights_date_is_measured_day_and_absent_value_is_nan(page_insights):
    df = page_insights([
        {"name": "page_impressions", "values": [
            {"end_time": "2024-01-02T08:00:00+0000", "value": 10},
            {"end_time": "2024-01-03T08:00:00+0000"},
        ]},
    ], ["page_impressions"])
    assert df["date"].astype(str).tolist() == ["2024-01-01", "2024-01-02"]
    assert df["page_impressions"].iloc[0] == 10
    assert pd.isna(df["page_impressions"].iloc[1])


def test_ad_insights_are_attributable_and_absent_metrics_are_nan(sdk):
    connector = sdk.module.FacebookBusinessConnector("tok")
    account = MagicMock()
    account.get_insights.return_value = iter([{
        "ad_id": "1", "ad_name": "A", "date_start": "2024-01-01",
        "date_stop": "2024-01-01", "impressions": "5",
    }])
    sdk.factories["AdAccount"].side_effect = None
    sdk.factories["AdAccount"].return_value = account
    df = connector.get_ad_insights("act_1", "2024-01-01", "2024-01-01")
    call = account.get_insights.call_args.kwargs
    assert {"ad_id", "ad_name", "date_start", "date_stop"} <= set(call["fields"])
    assert call["params"].get("time_increment") == 1
    assert {"ad_id", "date_start"} <= set(df.columns)
    assert pd.isna(df.loc[0, "clicks"])


def test_batch_docstring_matches_accepted_types_and_takes_config_directory():
    from siege_utilities.analytics.facebook_business import batch_retrieve_facebook_data
    assert "config_directory" in inspect.signature(batch_retrieve_facebook_data).parameters
    doc = batch_retrieve_facebook_data.__doc__
    assert all(t in doc for t in ("ad_account", "page", "business"))
