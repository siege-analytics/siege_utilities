"""Known integer counts render as integers next to unknown ones (#1812).

Emitting None for an omitted count makes a mixed column float, so a known 7
was rendered "7.0". Integral values render as integers; fractional and
unknown values keep their existing rendering.
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from siege_utilities.reporting.social_media_reports import (
    SocialMediaReportGenerator,
    _format_metric,
)

START, END = date(2026, 1, 1), date(2026, 1, 31)


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
