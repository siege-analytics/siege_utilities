"""Connector-to-report fixtures for PR #1812 B5; no rendering or HTTP."""

from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.analytics.x_twitter import XTwitterConnector
from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator

START, END = date(2026, 1, 1), date(2026, 1, 31)


@pytest.fixture
def assembler(monkeypatch):
    monkeypatch.setattr(requests.Session, "request", Mock(side_effect=AssertionError("Unexpected HTTP")))
    gen = object.__new__(SocialMediaReportGenerator)
    gen.client_name = "Dummy client"
    return gen


def platform(name="x_twitter", followers=None, posts=None):
    return {"platform": name, "account_info": {"followers_count": followers, "following_count": None},
            "posts": pd.DataFrame() if posts is None else posts, "insights": pd.DataFrame()}


def test_b5_connector_to_report_missing_public_metrics(assembler, monkeypatch):
    with XTwitterConnector("DUMMY_OLD_TOKEN", user_id="123") as client:
        client._authenticated = True
        monkeypatch.setattr(client, "_request", Mock(return_value={"data": {"id": "123", "public_metrics": {}}}))
        monkeypatch.setattr(client, "get_posts", Mock(return_value=pd.DataFrame()))
        monkeypatch.setattr(client, "get_account_insights", Mock(return_value=pd.DataFrame()))
        data = assembler._collect_platform_data([client], START, END)
    assert data[0]["account_info"]["followers_count"] is None
    report = assembler._build_report_data(data, START, END)
    assert "unavailable total followers" in report["executive_summary"]
    assert report["metrics"]["x_twitter — Followers"]["value"] == "unavailable"
    assert report["metrics"]["Total Followers (all platforms)"]["value"] == "unavailable"
    assert report["tables"][0]["data"][0][1:3] == ["unavailable", "unavailable"]
    assert data[0]["account_info"]["followers_count"] is None


@pytest.mark.parametrize("values,expected", [([None, None], "unavailable"), ([None, 23], "23"), ([None, 0], "0")])
def test_b5_totals_and_comparisons_use_known_values(assembler, values, expected):
    data = [platform(f"platform{i}", value) for i, value in enumerate(values)]
    report = assembler._build_report_data(data, START, END)
    assert report["metrics"]["Total Followers (all platforms)"]["value"] == expected
    assert f"{expected} total followers" in report["executive_summary"]
    assert report["metrics"]["platform0 — Followers"]["value"] == "unavailable"
    assert "nan" not in str(report).lower()
    if values == [None, 23]:
        assert report["charts"][0]["data"]["datasets"][0]["data"] == [None, 23]
    assert [d["account_info"]["followers_count"] for d in data] == values


@pytest.mark.parametrize("likes", [[None, None], [None, 0], [None, 12]])
def test_b5_nullable_post_metrics_at_every_numeric_site(assembler, likes):
    posts = pd.DataFrame({"text": ["unknown", "known"], "like_count": likes,
                          "reply_count": [None, None]})
    data = [platform(followers=5, posts=posts), platform("instagram", followers=None)]
    original = posts.copy(deep=True)
    report = assembler._build_report_data(data, START, END)
    table = next(t for t in report["tables"] if t["title"] == "Top Posts — X Twitter")
    unknown = next(row for row in table["data"] if row[0] == "unknown")
    assert unknown[1:3] == ["unavailable", "unavailable"]
    assert "nan" not in str(report).lower()
    if likes == [None, None]:
        assert not any("with 0 likes" in item for item in report["insights"])
    pd.testing.assert_frame_equal(posts, original)


@pytest.mark.parametrize("dtype", ["Int64", "Float64"])
def test_b5_nullable_series_and_chart_gaps(assembler, dtype):
    unknown = platform(followers=pd.NA, posts=pd.DataFrame({
        "text": ["unknown"], "like_count": pd.Series([pd.NA], dtype=dtype),
        "comments_count": [None],
    }))
    unknown["insights"] = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"], "reach": pd.Series([pd.NA, 2], dtype=dtype),
    })
    known = platform("instagram", 10, pd.DataFrame({"text": ["known"], "like_count": [12]}))
    report = assembler._build_report_data([unknown, known], START, END)
    likes = next(c for c in report["charts"] if c["title"] == "Total Likes by Platform")
    assert likes["data"]["datasets"][0]["data"] == [None, 12]
    daily = next(c for c in report["charts"] if c["type"] == "line")
    assert daily["data"]["datasets"][0]["data"] == [None, 2]
    assert "unavailable likes per post" in " ".join(report["insights"])


def test_b5_api_omitted_like_count_averages_known_only_end_to_end(assembler):
    """End-to-end: a tweet whose public_metrics omit like_count must not be
    averaged as 0. [12, missing] -> average 12, not 6; the converter emits None
    for the omitted count so the report's known-only average stays correct (#1458)."""
    posts = XTwitterConnector._tweets_to_dataframe([
        {"id": "a", "text": "hi", "public_metrics": {"like_count": 12}},
        {"id": "b", "text": "yo", "public_metrics": {}},
    ])
    data = [platform("x_twitter", followers=100, posts=posts)]
    report = assembler._build_report_data(data, START, END)
    joined = " ".join(report["insights"])
    assert "average 12 likes per post" in joined
    assert "average 6" not in joined
