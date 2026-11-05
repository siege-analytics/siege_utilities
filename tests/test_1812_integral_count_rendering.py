"""Known integer counts render as integers next to unknown ones (#1812).

Emitting None for an omitted count makes a mixed column float, so a known 7
was rendered "7.0". Integral values render as integers; fractional and
unknown values keep their existing rendering.
"""

from datetime import date

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
