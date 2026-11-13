"""Connector-to-report fixtures for PR #1812 B5; no rendering or HTTP."""

from datetime import date
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
import requests

from siege_utilities.analytics.x_twitter import XTwitterConnector
from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator, _format_metric

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
    table = next(t for t in report["tables"] if t["title"] == "Top analyzed posts — X Twitter")
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
    likes = next(c for c in report["charts"] if c["title"] == "Likes from analyzed posts by Platform")
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


# Largest-audience insight: a comparison needs two known follower counts.
def _audience_insights(assembler: SocialMediaReportGenerator, followers: list[object]) -> list[str]:
    data = [platform(f"platform{i}", value) for i, value in enumerate(followers)]
    report = assembler._build_report_data(data, START, END)
    return [line for line in report["insights"] if "largest audience" in line]


@pytest.mark.parametrize("followers", [[1234, None], [None, 1234], [None, 0]])
def test_one_known_follower_count_claims_no_largest_audience(
    assembler: SocialMediaReportGenerator, followers: list[object],
) -> None:
    # K=1 of M=2: nothing is compared, so no platform is called largest.
    assert _audience_insights(assembler, followers) == []


def test_all_known_follower_counts_name_the_largest_audience(assembler: SocialMediaReportGenerator) -> None:
    assert _audience_insights(assembler, [12, 30]) == [
        "Platform1 has the largest audience with 30 followers."
    ]


def test_partially_known_follower_counts_limit_the_claim(assembler: SocialMediaReportGenerator) -> None:
    # K=2 of M=3: the claim is scoped to the platforms with known counts.
    assert _audience_insights(assembler, [12, None, 30]) == [
        "Platform2 has the largest audience among the 2 of 3 platforms with known "
        "follower counts with 30 followers."
    ]


# Known integer counts render as integers next to unknown ones (#1812).
# Emitting None for an omitted count makes a mixed column float, so a known 7
# was rendered "7.0". Integral values render as integers; fractional and
# unknown values keep their existing rendering.
@pytest.mark.parametrize("value,spec,expected", [
    (7.0, "", "7"),
    (1234.0, ",", "1,234"),
    (7, "", "7"),
    (7.5, "", "7.5"),
    (12.4, ",.0f", "12"),
    (None, "", "unavailable"),
    (float("nan"), ",", "unavailable"),
    (pd.NA, ",", "unavailable"),
])
def test_format_metric_renders_integral_counts_as_integers(value, spec, expected):
    assert _format_metric(value, spec) == expected


@pytest.mark.parametrize("value,spec,expected", [
    (np.float32(1234.0), ",", "1,234"),
    (pd.array([1234.0], dtype="Float32")[0], ",", "1,234"),
    (np.float32(7.5), "", "7.5"),
    (np.float32(12.4), ",.0f", "12"),
])
def test_format_metric_handles_numpy_floating_counts(value, spec, expected):
    assert _format_metric(value, spec) == expected


class _Float32Connector:
    """Connector stand-in whose account info carries pandas Float32 counts."""

    platform_name = "instagram"

    def get_account_info(self):
        counts = pd.array([1234.0, 2.0], dtype="Float32")
        return {"followers_count": counts[0], "follows_count": counts[1]}

    def get_account_insights(self, start, end):
        return pd.DataFrame()

    def get_posts(self, *args, **kwargs):
        return pd.DataFrame()


def test_float32_follower_count_renders_as_integer_end_to_end():
    gen = object.__new__(SocialMediaReportGenerator)
    gen.client_name = "Dummy client"
    data = gen._collect_platform_data([_Float32Connector()], START, END)
    assert isinstance(data[0]["account_info"]["followers_count"], np.floating)
    report = gen._build_report_data(data, START, END)
    followers = {name: entry["value"] for name, entry in report["metrics"].items() if "Followers" in name}
    assert len(followers) == 2
    assert all(value == "1,234" for value in followers.values()), followers


def test_float32_count_next_to_missing_platform_count():
    # The [4.1.0] claim: a known count renders as an integer next to a
    # missing one. Instagram reports a float32 follower count, X omits it.
    posts = pd.DataFrame({"text": ["known"],
                          "like_count": pd.array([7.0], dtype="Float32"),
                          "comments_count": pd.array([1.0], dtype="Float32")})
    data = [
        {"platform": "instagram", "account_info": {"followers_count": np.float32(1234)},
         "posts": posts, "insights": pd.DataFrame()},
        {"platform": "x_twitter", "account_info": {"followers_count": None},
         "posts": pd.DataFrame(), "insights": pd.DataFrame()},
    ]
    gen = object.__new__(SocialMediaReportGenerator)
    gen.client_name = "Dummy client"
    report = gen._build_report_data(data, START, END)
    metrics = {name: entry["value"] for name, entry in report["metrics"].items()}
    assert metrics["instagram — Followers"] == "1,234"
    assert metrics["x_twitter — Followers"] == "unavailable"
    assert metrics["Total Followers (all platforms)"] == "1,234"
    # Control: the Float32 posts row already rendered as integers.
    rows = {row[0]: row[1:3] for table in report["tables"]
            if table["headers"][:2] == ["Post", "Likes"] for row in table["data"]}
    assert rows["known"] == ["7", "1"]


def test_top_posts_table_shows_known_like_count_as_integer():
    posts = pd.DataFrame({"text": ["omitted", "known"], "like_count": [None, 7],
                          "comments_count": [None, 1]})
    data = [{"platform": "instagram", "account_info": {"followers_count": 1234.0},
             "posts": posts, "insights": pd.DataFrame()}]
    gen = object.__new__(SocialMediaReportGenerator)
    gen.client_name = "Dummy client"
    report = gen._build_report_data(data, START, END)
    rows = {row[0]: row[1:3] for table in report["tables"]
            if table["headers"][:2] == ["Post", "Likes"] for row in table["data"]}
    assert rows["known"] == ["7", "1"]
    assert rows["omitted"] == ["unavailable", "unavailable"]
    followers = [entry["value"] for name, entry in report["metrics"].items() if "Followers" in name]
    assert followers and all(value == "1,234" for value in followers)
