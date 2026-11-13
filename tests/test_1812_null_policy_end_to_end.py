"""An unavailable social metric stays None end to end, never 0 (#1812, #1807).

Real Instagram and X converter output for posts that omit their counts flows
into the report builder. The assertions avoid report wording, so the same test
runs on this PR alone and on a tree that also carries #1807's report changes.
"""

from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.analytics.instagram import InstagramConnector
from siege_utilities.analytics.x_twitter import XTwitterConnector
from siege_utilities.reporting.social_media_reports import SocialMediaReportGenerator

START, END = date(2026, 1, 1), date(2026, 1, 31)

IG_POSTS = [
    {"id": "1", "caption": "Omitted counts", "timestamp": "2026-01-02T01:02:03+0000"},
    {"id": "2", "caption": "Known counts", "timestamp": "2026-01-03T01:02:03+0000",
     "like_count": 7, "comments_count": 1},
]
X_POSTS = [{"id": "3", "text": "Omitted metrics", "created_at": "2026-01-04T01:02:03Z"}]


@pytest.fixture
def report(monkeypatch):
    monkeypatch.setattr(requests.Session, "request", Mock(side_effect=AssertionError("Unexpected HTTP")))
    instagram_posts = InstagramConnector._posts_to_dataframe(IG_POSTS)
    x_posts = XTwitterConnector._tweets_to_dataframe(X_POSTS)
    data = [
        {"platform": "instagram", "account_info": {"followers_count": None, "follows_count": None},
         "posts": instagram_posts, "insights": pd.DataFrame()},
        {"platform": "x_twitter", "account_info": {"followers_count": None, "following_count": None},
         "posts": x_posts, "insights": pd.DataFrame()},
    ]
    gen = object.__new__(SocialMediaReportGenerator)
    gen.client_name = "Dummy client"
    return instagram_posts, x_posts, gen._build_report_data(data, START, END)


def test_converters_emit_none_for_omitted_counts(report):
    # Missing, never 0. A column that also holds a known count is float, so
    # the omitted cell is NaN there; an all-omitted column keeps None.
    instagram_posts, x_posts, _ = report
    assert pd.isna(instagram_posts.loc[0, "like_count"])
    assert pd.isna(instagram_posts.loc[0, "comments_count"])
    assert instagram_posts.loc[1, "like_count"] == 7
    for column in ("like_count", "retweet_count", "reply_count", "quote_count"):
        assert x_posts.loc[0, column] is None, column


def test_unknown_followers_render_unavailable(report):
    *_, built = report
    followers = {name: entry["value"] for name, entry in built["metrics"].items() if "Followers" in name}
    assert followers
    assert all(value == "unavailable" for value in followers.values()), followers


def test_omitted_like_counts_never_render_as_zero(report):
    *_, built = report
    top_posts = [table for table in built["tables"] if table["headers"][:2] == ["Post", "Likes"]]
    assert top_posts
    likes = {row[0]: row[1] for table in top_posts for row in table["data"]}
    assert float(likes["Known counts"]) == 7
    assert likes["Omitted counts"] == "unavailable"
    assert likes["Omitted metrics"] == "unavailable"


def test_all_unknown_engagement_is_none_not_zero(report):
    *_, built = report
    engagement = [chart for chart in built["charts"] if chart["data"]["datasets"][0]["label"] == "Likes"]
    assert engagement
    values = dict(zip(engagement[0]["data"]["labels"], engagement[0]["data"]["datasets"][0]["data"]))
    assert values["instagram"] == 7
    assert values["x_twitter"] is None
