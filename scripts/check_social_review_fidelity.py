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
    source = subprocess.check_output(
        ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True, timeout=30,
    )
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


import numbers


def _is_null(value):
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _is_zero(value):
    return (
        isinstance(value, numbers.Number)
        and not isinstance(value, bool)
        and not _is_null(value)
        and value == 0
    )


def compare(old, new, where="root"):
    """Count ONLY the intended baseline-zero -> current-null differences.

    Returns the number of cells where the pre-fix baseline held a fabricated
    numeric zero and the post-fix output is null (the omitted IG/X count fix).
    EVERY other value, row, column, index key and timestamp must match exactly;
    any other difference raises, so a new unexplained removal or relabel fails
    the audit rather than being silently absorbed.
    """
    if isinstance(old, pd.DataFrame) or isinstance(new, pd.DataFrame):
        assert isinstance(old, pd.DataFrame) and isinstance(new, pd.DataFrame), (where, type(old), type(new))
        assert list(old.columns) == list(new.columns), (where, list(old.columns), list(new.columns))
        assert list(old.index) == list(new.index), (where, list(old.index), list(new.index))
        allowed = 0
        for col in old.columns:
            for idx in old.index:
                allowed += compare(old.at[idx, col], new.at[idx, col], f"{where}[{idx!r},{col!r}]")
        return allowed
    if isinstance(old, dict) or isinstance(new, dict):
        assert isinstance(old, dict) and isinstance(new, dict), (where, type(old), type(new))
        assert set(old) == set(new), (where, set(old), set(new))
        return sum(compare(old[key], new[key], f"{where}.{key}") for key in old)
    if isinstance(old, (list, tuple)) or isinstance(new, (list, tuple)):
        assert type(old) is type(new) and len(old) == len(new), (where, old, new)
        return sum(compare(o, n, f"{where}[{i}]") for i, (o, n) in enumerate(zip(old, new)))
    if _is_null(old) and _is_null(new):
        return 0
    if _is_null(old) != _is_null(new):
        if _is_zero(old) and _is_null(new):
            return 1
        raise AssertionError(f"unexpected null/non-null diff at {where}: {old!r} -> {new!r}")
    if old == new:
        return 0
    raise AssertionError(f"unexpected value diff at {where}: {old!r} -> {new!r}")


# The audit permits exactly this many baseline-zero -> current-null cells: the
# omitted-count fix produces 2 Instagram and 6 X cells across the 23 fixtures.
# Any other count fails, so a new leak (or a lost intended null) is caught.
_EXPECTED_ABSENT_ZERO_TO_NULL = 8


def audit():
    count = 0
    allowed = 0
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
            allowed += compare(before, after, f"{platform}.{converter}")
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
                allowed += compare(before, after, f"{platform}.{method}")
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
            allowed += compare(reports[0], reports[1], "report")
        else:
            assert reports[0] == "TypeError"
            assert isinstance(reports[1], dict)
            known = [v for v in values if v is not None]
            expected = str(sum(known)) if known else "unavailable"
            assert reports[1]["metrics"]["Total Followers (all platforms)"]["value"] == expected
            assert reports[1]["metrics"]["x_twitter — Followers"]["value"] == "unavailable"
            assert data[0]["account_info"]["followers_count"] is None
        count += 1
    assert allowed == _EXPECTED_ABSENT_ZERO_TO_NULL, (
        f"expected exactly {_EXPECTED_ABSENT_ZERO_TO_NULL} baseline-zero -> null "
        f"count cells, classified {allowed}"
    )
    print(
        f"old/new diff: {allowed} baseline-zero -> null count cells "
        f"(the intended omitted IG/X fix), 0 other differences ({count} fixtures)"
    )


if __name__ == "__main__":
    with patch.object(requests.Session, "request", side_effect=AssertionError("Unexpected HTTP")):
        audit()
