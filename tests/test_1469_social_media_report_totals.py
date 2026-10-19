"""Regression coverage for social report failures, sample counts and missing metrics."""

from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest

from siege_utilities.analytics._social_protocol import SocialMediaError
from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator


START = date(2026, 1, 1)
END = date(2026, 3, 31)


class FakeConnector:
    def __init__(
        self, platform_name="fakebook", *, followers=10, following=5,
        posts=None, insights=None, failure=None, error=None,
    ):
        self.platform_name = platform_name
        self.followers = followers
        self.following = following
        self.posts = posts if posts is not None else pd.DataFrame()
        self.insights = insights if insights is not None else pd.DataFrame()
        self.failure = failure
        self.error = error
        self.post_requests = []

    def get_account_info(self):
        if self.failure == "get_account_info":
            raise self.error
        return {"followers_count": self.followers, "following_count": self.following}

    def get_account_insights(self, start_date, end_date):
        assert (start_date, end_date) == (START, END)
        if self.failure == "get_account_insights":
            raise self.error
        return self.insights

    def get_posts(self, start_date, end_date, *, limit):
        self.post_requests.append((start_date, end_date, limit))
        if self.failure == "get_posts":
            raise self.error
        return self.posts.head(limit)


@pytest.fixture
def report(tmp_path, monkeypatch):
    generator = SocialMediaReportGenerator("client", output_dir=tmp_path)
    writer = Mock(return_value=tmp_path / "report.pdf")
    monkeypatch.setattr(generator.report_generator, "create_analytics_report", writer)
    return generator, writer


@pytest.mark.parametrize("method", ["get_posts", "get_account_info", "get_account_insights"])
@pytest.mark.parametrize("error_type", [RuntimeError, SocialMediaError])
def test_connector_failure_raises_with_platform_and_cause(report, method, error_type):
    generator, writer = report
    cause = error_type("retrieval failed")
    connector = FakeConnector(failure=method, error=cause)

    with pytest.raises(SocialMediaError, match="fakebook.*retrieval failed") as exc:
        generator.create_social_media_report([FakeConnector("healthy"), connector], START, END)

    assert exc.value.__cause__ is cause
    writer.assert_not_called()


@pytest.mark.parametrize("posts_limit", [None, 75], ids=["default-50", "custom-75"])
def test_post_counts_and_engagement_are_labeled_as_samples(report, posts_limit):
    generator, writer = report
    posts = pd.DataFrame({
        "text": [f"Post {i}" for i in range(120)],
        "like_count": range(120),
    })
    connectors = [FakeConnector(posts=posts), FakeConnector("other", posts=posts.head(3))]
    kwargs = {} if posts_limit is None else {"posts_limit": posts_limit}
    limit = posts_limit or 50

    output = generator.create_social_media_report(connectors, START, END, **kwargs)

    assert output == writer.return_value
    assert all(c.post_requests == [(START, END, limit)] for c in connectors)
    payload = writer.call_args.args[0]
    summary = payload["executive_summary"]
    assert f"{limit + 3} posts analyzed" in summary
    assert f"most recent up to {limit} per platform" in summary
    assert "posts in the reporting window" not in summary
    metrics = payload["metrics"]
    assert "Total Posts (all platforms)" not in metrics
    assert metrics[f"fakebook — Posts analyzed (most recent up to {limit})"]["value"] == str(limit)
    assert metrics[f"Posts analyzed (all platforms; most recent up to {limit} each)"]["value"] == str(limit + 3)
    comparison = payload["tables"][0]
    assert comparison["headers"][-1] == f"Posts analyzed (most recent up to {limit})"
    assert comparison["data"][0][-1] == str(limit)
    assert "analyzed posts" in payload["charts"][1]["title"]
    assert all("analyzed posts" in table["title"] for table in payload["tables"][1:])
    post_insights = [line for line in payload["insights"] if "post" in line]
    assert post_insights
    assert all("analyzed posts" in line for line in post_insights)


@pytest.mark.parametrize("missing_followers", [None, float("nan"), pd.NA])
@pytest.mark.parametrize("missing_likes", [None, float("nan"), pd.NA])
def test_missing_counts_and_all_missing_likes_aggregate_as_zero(
    report, missing_followers, missing_likes,
):
    generator, writer = report
    posts = pd.DataFrame({"text": ["one", "two"], "like_count": [missing_likes] * 2})
    connector = FakeConnector(followers=missing_followers, following=missing_followers, posts=posts)
    other = FakeConnector("other", followers=0, following=0)

    generator.create_social_media_report([connector, other], START, END)

    payload = writer.call_args.args[0]
    assert "0 total followers" in payload["executive_summary"]
    assert payload["metrics"]["Total Followers (all platforms)"]["value"] == "0"
    assert payload["metrics"]["fakebook — Followers"]["value"] == "0"
    assert payload["charts"] == []
    assert payload["tables"][0]["data"][0][1:3] == ["0", "0"]
    assert all(row[1] == "0" for row in payload["tables"][1]["data"])
    assert any("average 0 likes" in line for line in payload["insights"])
    assert not any("Top performing" in line for line in payload["insights"])
    assert "nan" not in str(payload).lower()
    assert "<NA>" not in str(payload)


def test_missing_metrics_do_not_change_known_counts_or_rankings(report):
    generator, writer = report
    posts = pd.DataFrame({
        "text": ["unknown", "popular", "quiet"],
        "like_count": pd.Series([pd.NA, 6, 0], dtype="Int64"),
        "comments_count": pd.Series([pd.NA, 2, 0], dtype="Int64"),
    })
    missing = FakeConnector(followers=None, posts=posts.head(1))
    known = FakeConnector("known", followers=12, posts=posts)

    generator.create_social_media_report([missing, known], START, END)

    payload = writer.call_args.args[0]
    assert payload["metrics"]["Total Followers (all platforms)"]["value"] == "12"
    assert payload["charts"][0]["data"]["datasets"][0]["data"] == [0, 12]
    assert payload["charts"][1]["data"]["datasets"][0]["data"] == [0, 6]
    assert "Known has the largest audience with 12 followers." in payload["insights"]
    assert any('"popular…" with 6 likes' in line for line in payload["insights"])
    assert "<NA>" not in str(payload)


@pytest.mark.parametrize("dtype", ["Int64", "Float64", "int32", "float32"])
def test_numeric_insights_include_nullable_and_narrow_dtypes(report, dtype):
    generator, writer = report
    nullable = dtype[0].isupper()
    insights = pd.DataFrame({
        "date": [START, END],
        "reach": pd.Series([3, None if nullable else 2], dtype=dtype),
        "label": ["start", "end"],
        "active": pd.Series([True, None], dtype="boolean"),
    })
    generator.create_social_media_report([FakeConnector(insights=insights)], START, END)

    charts = writer.call_args.args[0]["charts"]
    daily = next(chart for chart in charts if chart["type"] == "line")
    assert daily["data"]["datasets"] == [{"label": "Reach", "data": [3, 0 if nullable else 2]}]


@pytest.mark.parametrize("posts_limit", [0, -1, 1.5, True, None])
def test_invalid_posts_limit_fails_before_retrieval(report, posts_limit):
    generator, writer = report
    connector = Mock()

    with pytest.raises(ValueError, match="posts_limit must be a positive integer"):
        generator.create_social_media_report([connector], START, END, posts_limit=posts_limit)

    assert connector.mock_calls == []
    writer.assert_not_called()
