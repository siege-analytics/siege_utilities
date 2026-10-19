"""Compare offline social outputs with PR #1812's reviewed head.

Run with the repository on PYTHONPATH. Requires local git object d329eef7;
loads its three modules in memory without changing tracked files. No HTTP.
"""

from copy import deepcopy
from datetime import date
from pathlib import Path
import subprocess
from types import ModuleType
from unittest.mock import Mock, patch

import pandas as pd
import requests

from siege_utilities.analytics import instagram, x_twitter
from siege_utilities.reporting import social_media_reports

BASELINE = "d329eef7a4e001a8ce30cc3fc6b7ce49c1acb4ff"
ROOT = Path(__file__).resolve().parents[1]
START, END = date(2026, 1, 1), date(2026, 1, 31)


def old_module(module):
    path = Path(module.__file__).relative_to(ROOT).as_posix()
    source = subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True)
    old = ModuleType("baseline_" + module.__name__.rsplit(".", 1)[-1])
    exec(compile(source, f"{BASELINE}:{path}", "exec"), old.__dict__)
    return old


def client_for(module, platform, body):
    if platform == "instagram":
        client = module.InstagramConnector("DUMMY_OLD_TOKEN", ig_user_id="123")
    else:
        client = module.XTwitterConnector("DUMMY_OLD_TOKEN", user_id="123")
    client._authenticated = True
    client._request = Mock(side_effect=lambda *args, **kwargs: deepcopy(body))
    return client


def assert_equal(old, new):
    if isinstance(old, pd.DataFrame):
        pd.testing.assert_frame_equal(old, new)
    else:
        assert old == new, (old, new)


def audit():
    count = 0
    for platform, current in (("instagram", instagram), ("x", x_twitter)):
        old = old_module(current)
        class_name = "InstagramConnector" if platform == "instagram" else "XTwitterConnector"
        converter = "_posts_to_dataframe" if platform == "instagram" else "_tweets_to_dataframe"
        if platform == "instagram":
            populated = [{"id": "123", "caption": "Dummy text", "media_type": "IMAGE",
                          "media_url": "https://example.invalid/image", "permalink": "https://example.invalid/post",
                          "timestamp": "2026-01-02T01:02:03.456+0000", "like_count": 0, "comments_count": 4}]
            account = {"id": "123", "username": "dummy", "followers_count": 0,
                       "follows_count": 4, "media_count": 12}
            account_empty = {"id": "123"}
            insights = {"data": [{"name": "reach", "values": [{"end_time": "2026-01-02", "value": 0}]}]}
            insights_empty = {"data": [{"name": "reach", "values": [{"end_time": "2026-01-02"}]}]}
            post_insights = {"data": [{"name": "views", "total_value": {"value": 0}},
                                      {"name": "reach", "values": [{"value": 12}]}]}
            post_empty = {"data": [{"name": "views", "values": []}]}
        else:
            populated = [{"id": "123", "text": "Dummy text", "created_at": "2026-01-02T01:02:03.456Z",
                          "public_metrics": {"like_count": 0, "retweet_count": 1, "reply_count": 2,
                                             "quote_count": 3, "bookmark_count": 4, "impression_count": 5}}]
            account = {"data": {"id": "123", "username": "dummy", "public_metrics": {
                "followers_count": 0, "following_count": 4, "tweet_count": 12, "listed_count": 2, "like_count": 1,
            }}}
            account_empty = {"data": {"id": "123", "public_metrics": {}}}
            insights, insights_empty = account, account_empty
            post_insights = {"data": {"public_metrics": {"like_count": 0},
                                      "non_public_metrics": {"like_count": 3, "url_link_clicks": 7},
                                      "organic_metrics": {"url_link_clicks": 2, "user_profile_clicks": 9}}}
            post_empty = {"data": {"public_metrics": {}}}
        for posts in ([], populated, [{"id": "123"}]):
            before = getattr(getattr(old, class_name), converter)(deepcopy(posts))
            after = getattr(getattr(current, class_name), converter)(deepcopy(posts))
            assert_equal(before, after)
            count += 1
        for method, args, bodies in (
            ("get_account_info", (), (account, account_empty)),
            ("get_account_insights", (START, END), (insights, insights_empty)),
            ("get_post_insights", ("123",), (post_insights, post_empty)),
        ):
            for body in bodies:
                with client_for(old, platform, body) as previous, client_for(current, platform, body) as new:
                    before = getattr(previous, method)(*args)
                    after = getattr(new, method)(*args)
                assert_equal(before, after)
                if platform == "x" and method == "get_account_info" and body == account_empty:
                    assert after["followers_count"] is None
                count += 1

    old_report = old_module(social_media_reports)
    for values in ([12, 3], [0, 0], [None, None], [None, 12], [None, 0]):
        data = [{"platform": name, "account_info": {"followers_count": followers, "following_count": 2},
                 "posts": pd.DataFrame({"text": ["Dummy post"], "like_count": [4], "reply_count": [0],
                                        "published_at": ["2026-01-02"]}),
                 "insights": pd.DataFrame({"date": ["2026-01-02"], "reach": [0]})}
                for name, followers in zip(("x_twitter", "instagram"), values)]
        reports = []
        for module in (old_report, social_media_reports):
            gen = object.__new__(module.SocialMediaReportGenerator)
            gen.client_name = "Dummy client"
            try:
                reports.append(gen._build_report_data(deepcopy(data), START, END))
            except TypeError:
                reports.append("TypeError")
        if None not in values:
            assert_equal(*reports)
        else:
            assert reports[0] == "TypeError"
            assert isinstance(reports[1], dict)
            known = [v for v in values if v is not None]
            expected = str(sum(known)) if known else "unavailable"
            assert reports[1]["metrics"]["Total Followers (all platforms)"]["value"] == expected
            assert reports[1]["metrics"]["x_twitter — Followers"]["value"] == "unavailable"
            assert data[0]["account_info"]["followers_count"] is None
        count += 1
    print(f"old/new diff: 0 unexplained removals ({count} fixtures)")


if __name__ == "__main__":
    with patch.object(requests.Session, "request", side_effect=AssertionError("Unexpected HTTP")):
        audit()
