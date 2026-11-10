"""Compare offline social outputs with PR #1812's reviewed head.

Run with the repository on PYTHONPATH. The three baseline modules are frozen
byte-identical copies of d329eef7 under tests/fixtures/, checked by git blob
id, so no git history is needed (shallow CI checkouts work). Loads them in
memory without changing tracked files. No HTTP.
"""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import numbers
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import Mock, patch

import pandas as pd
import requests

from siege_utilities.analytics import instagram, x_twitter
from siege_utilities.reporting import social_media_reports

BASELINE = "d329eef7a4e001a8ce30cc3fc6b7ce49c1acb4ff"
ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "tests" / "fixtures" / "social_baseline_d329eef7"
# Git blob ids of the three modules at BASELINE; each frozen copy must match.
BASELINE_BLOBS = {
    "siege_utilities/analytics/instagram.py": "7cafa6ca1291ea56465f083f16dd69bcd436f93b",
    "siege_utilities/analytics/x_twitter.py": "da2b74e6c60e7310979dd794a1713fc70e7e0f86",
    "siege_utilities/reporting/social_media_reports.py": "cd03465874f1f56ce35d5913b437dc47341f8ec7",
}
START, END = date(2026, 1, 1), date(2026, 1, 31)


def git_blob_id(data: bytes) -> str:
    """The id ``git hash-object`` assigns to ``data``."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def old_module(module: ModuleType) -> ModuleType:
    path = Path(module.__file__).relative_to(ROOT).as_posix()
    frozen = FROZEN / (Path(path).name + ".txt")
    data = frozen.read_bytes()
    if git_blob_id(data) != BASELINE_BLOBS[path]:
        raise AssertionError(
            f"{frozen} is not {BASELINE}:{path}: blob {git_blob_id(data)}, "
            f"expected {BASELINE_BLOBS[path]}"
        )
    source = data.decode("utf-8")
    old = ModuleType("baseline_" + module.__name__.rsplit(".", 1)[-1])
    exec(compile(source, f"{BASELINE}:{path}", "exec"), old.__dict__)
    return old


def client_for(module: ModuleType, platform: str, body: object) -> Any:
    if platform == "instagram":
        client = module.InstagramConnector("DUMMY_OLD_TOKEN", ig_user_id="123")
    else:
        client = module.XTwitterConnector("DUMMY_OLD_TOKEN", user_id="123")
    client._authenticated = True
    client._request = Mock(side_effect=lambda *args, **kwargs: deepcopy(body))
    return client


def _is_null(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _is_zero(value: object) -> bool:
    return (
        isinstance(value, numbers.Number)
        and not isinstance(value, bool)
        and not _is_null(value)
        and value == 0
    )


# Baseline-zero -> current-null is authorized ONLY at these explicit
# omitted-post converter cells: the pre-fix code fabricated 0 for a post that
# omitted the metric, the fix returns null. Two Instagram columns and six X
# columns, each at the single omitted-post row. A zero -> null anywhere else is
# a leak and a missing authorized location is a lost intended null; an aggregate
# total is a useful check, not authorization (#1812 R-1812-3).
_AUTHORIZED = frozenset({
    "instagram._posts_to_dataframe.omitted[0,'like_count']",
    "instagram._posts_to_dataframe.omitted[0,'comments_count']",
    "x._tweets_to_dataframe.omitted[0,'retweet_count']",
    "x._tweets_to_dataframe.omitted[0,'reply_count']",
    "x._tweets_to_dataframe.omitted[0,'like_count']",
    "x._tweets_to_dataframe.omitted[0,'quote_count']",
    "x._tweets_to_dataframe.omitted[0,'bookmark_count']",
    "x._tweets_to_dataframe.omitted[0,'impression_count']",
})


def _strict_equal(old: object, new: object) -> bool:
    """Type-exact and timezone-exact leaf equality.

    Ordinary ``==`` certifies a same-instant timezone relabel (UTC vs local), a
    0 -> False value/type change, and other type coincidences as equal. The
    audit preserves exact representation, so compare the type and, for
    timestamps, the timezone and the instant.
    """
    if isinstance(old, pd.Timestamp) or isinstance(new, pd.Timestamp):
        if not (isinstance(old, pd.Timestamp) and isinstance(new, pd.Timestamp)):
            return False
        return old.tz == new.tz and old == new
    if type(old) is not type(new):
        return False
    return bool(old == new)


# #1444 (#1778, already in develop) relabels daily account insights: an Instagram
# row carries the day its value covers, one day before Graph's end_time marker,
# and an X snapshot carries the UTC date. Only these 'date' cells may differ from
# the frozen baseline, and only by exactly that rule (#1812).
_RELABELED: set[str] = set()


def _is_1444_relabel(old: object, new: object, where: str) -> bool:
    if not (isinstance(old, str) and isinstance(new, str)):
        return False
    if where.startswith("instagram.get_account_insights[") and where.endswith(",'date']"):
        try:
            return new == (date.fromisoformat(old) - timedelta(days=1)).isoformat()
        except ValueError:
            return False
    if where == "x.get_account_insights[0,'date']":
        return new == datetime.now(timezone.utc).date().isoformat()
    return False


def compare(old: object, new: object, where: str, hits: set[str]) -> int:
    """Count ONLY the authorized baseline-zero -> current-null cells.

    ``hits`` accumulates the authorized locations actually seen, so the caller
    asserts every intended null occurred and a compensating difference cannot
    mask a lost null. EVERY other value, row, column, index key/name, column
    dtype, type and timestamp must match exactly; any other difference raises,
    so a new unexplained removal, relabel or type change fails the audit. A
    column dtype may change only where an authorized null landed in it.
    """
    if isinstance(old, pd.DataFrame) or isinstance(new, pd.DataFrame):
        assert isinstance(old, pd.DataFrame) and isinstance(new, pd.DataFrame), (where, type(old), type(new))
        assert list(old.columns) == list(new.columns), (where, list(old.columns), list(new.columns))
        assert list(old.index) == list(new.index), (where, list(old.index), list(new.index))
        # Axis labels compare equal across representations (0 == 0.0), so the
        # axis type, dtype and name must match too.
        for axis in ("index", "columns"):
            before, after = getattr(old, axis), getattr(new, axis)
            assert type(before) is type(after), (where, axis, type(before), type(after))
            assert before.dtype == after.dtype, (where, axis, before.dtype, after.dtype)
            assert before.names == after.names, (where, axis, before.names, after.names)
        allowed = 0
        before = set(hits)
        for col in old.columns:
            for idx in old.index:
                allowed += compare(old.at[idx, col], new.at[idx, col], f"{where}[{idx!r},{col!r}]", hits)
        # Equal cells can hide a column dtype change (e.g. tz-aware datetime to
        # object). Only a column holding an authorized null may change dtype.
        new_hits = hits - before
        for col in old.columns:
            if old[col].dtype == new[col].dtype:
                continue
            if any(hit.startswith(f"{where}[") and hit.endswith(f",{col!r}]") for hit in new_hits):
                continue
            raise AssertionError(
                f"unexpected dtype change at {where}[{col!r}]: {old[col].dtype} -> {new[col].dtype}"
            )
        return allowed
    if isinstance(old, dict) or isinstance(new, dict):
        assert isinstance(old, dict) and isinstance(new, dict), (where, type(old), type(new))
        assert set(old) == set(new), (where, set(old), set(new))
        return sum(compare(old[key], new[key], f"{where}.{key}", hits) for key in old)
    if isinstance(old, (list, tuple)) or isinstance(new, (list, tuple)):
        assert type(old) is type(new) and len(old) == len(new), (where, old, new)
        return sum(compare(o, n, f"{where}[{i}]", hits) for i, (o, n) in enumerate(zip(old, new)))
    if _is_null(old) and _is_null(new):
        # None, pd.NA, NaT and NaN are distinct missing-value representations.
        if type(old) is not type(new):
            raise AssertionError(f"unexpected null type change at {where}: {old!r} -> {new!r}")
        return 0
    if _is_null(old) != _is_null(new):
        if _is_zero(old) and _is_null(new) and where in _AUTHORIZED:
            hits.add(where)
            return 1
        raise AssertionError(f"unexpected null/non-null diff at {where}: {old!r} -> {new!r}")
    if _strict_equal(old, new):
        return 0
    if _is_1444_relabel(old, new, where):
        _RELABELED.add(where.split("[", 1)[0])
        return 0
    raise AssertionError(f"unexpected value diff at {where}: {old!r} -> {new!r}")


def audit() -> None:
    count = 0
    allowed = 0
    hits = set()
    _RELABELED.clear()
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
        for label, posts in (("empty", []), ("populated", populated), ("omitted", [{"id": "123"}])):
            before = getattr(getattr(old, class_name), converter)(deepcopy(posts))
            after = getattr(getattr(current, class_name), converter)(deepcopy(posts))
            allowed += compare(before, after, f"{platform}.{converter}.{label}", hits)
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
                allowed += compare(before, after, f"{platform}.{method}", hits)
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
            allowed += compare(reports[0], reports[1], "report", hits)
        else:
            assert reports[0] == "TypeError"
            assert isinstance(reports[1], dict)
            known = [v for v in values if v is not None]
            expected = str(sum(known)) if known else "unavailable"
            assert reports[1]["metrics"]["Total Followers (all platforms)"]["value"] == expected
            assert reports[1]["metrics"]["x_twitter — Followers"]["value"] == "unavailable"
            assert data[0]["account_info"]["followers_count"] is None
        count += 1
    assert "instagram.get_account_insights" in _RELABELED, (
        "#1444 covered-day relabel of Instagram account insights was not exercised"
    )
    assert hits == _AUTHORIZED, (
        "authorized zero -> null locations differ from those observed; "
        f"missing {sorted(_AUTHORIZED - hits)}, unexpected {sorted(hits - _AUTHORIZED)}"
    )
    assert allowed == len(_AUTHORIZED), (allowed, len(_AUTHORIZED))
    print(
        f"old/new diff: {allowed} baseline-zero -> null count cells "
        f"(the intended omitted IG/X fix), 0 other differences ({count} fixtures)"
    )


if __name__ == "__main__":
    with patch.object(requests.Session, "request", side_effect=AssertionError("Unexpected HTTP")):
        audit()
