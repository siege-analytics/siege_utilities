"""Compare offline social outputs with PR #1812's reviewed head.

Run with the repository on PYTHONPATH. The three baseline modules are frozen
byte-identical copies of d329eef7 under tests/fixtures/, checked by git blob
id, so no git history is needed (shallow CI checkouts work). Loads them in
memory without changing tracked files. No HTTP.
"""

from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import numbers
from pathlib import Path
import re
from types import ModuleType
from typing import Any
from unittest.mock import Mock, patch

import numpy as np
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


def _is_temporal(value: object) -> bool:
    """Whether ``value`` is a date/time value or a date/time missing marker (NaT)."""
    return value is pd.NaT or isinstance(
        value, (np.datetime64, np.timedelta64, date, datetime, timedelta, pd.Timestamp, pd.Timedelta)
    )


def _is_scalar_count_unknown(value: object) -> bool:
    """Whether ``value`` is a SCALAR unknown count: None, pd.NA or float NaN.

    Only these may replace a baseline 0 at an authorized cell. A container
    (ndarray of any shape, Series, list...) holding a missing element can make
    ``pd.isna`` truthy, but it is not a count: ``pd.to_numeric`` rejects it and
    the report builder raises on it. Temporal missing markers (NaT) are not
    counts either (#1880).
    """
    if value is None or value is pd.NA:
        return True
    return isinstance(value, (float, np.floating)) and bool(np.isnan(value))


def _is_count_null_dtype(dtype: object) -> bool:
    """Whether a column dtype can hold an unknown count: numeric (not bool) or object.

    A datetime or timedelta column also holds a missing value (NaT) but is not
    a count domain; numeric arithmetic on it raises (#1880).
    """
    return (pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_bool_dtype(dtype)) or (
        pd.api.types.is_object_dtype(dtype)
    )


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

# #1469 rewords the report so post metrics read as a capped sample of the most
# recent posts. Before the unchanged strict comparison, these fixed rules turn
# the FROZEN BASELINE report's wording into #1469's. The rules are literal and
# never derived from the current report. Each rewrite is recorded by fixture
# case, rule, slot kind (dict key, dict value, comparison-table header) and its
# ORIGINAL baseline path. The record must equal _1469_EXPECTED_REWRITES
# exactly, so a missing, duplicate, excess, moved or undeclared rewrite fails.
# Every value, null and other string must still match exactly.
_POSTS_LIMIT = 50
_1469_STRINGS = {
    "Total Likes by Platform": "Likes from analyzed posts by Platform",
    "Total Posts (all platforms)": (
        f"Posts analyzed (all platforms; most recent up to {_POSTS_LIMIT} each)"
    ),
}
_1469_PATTERNS = (
    ("platform posts metric key", re.compile(r"^(\w+) — Posts$"),
     rf"\1 — Posts analyzed (most recent up to {_POSTS_LIMIT})"),
    ("top posts table title", re.compile(r"^Top Posts — (.+)$"), r"Top analyzed posts — \1"),
    ("executive summary", re.compile(r"^(Cross-platform social media report .+ posts) in the reporting window\.$"),
     rf"\1 analyzed (most recent up to {_POSTS_LIMIT} per platform within the reporting window). "
     "Post metrics describe this sample."),
    ("average likes insight", re.compile(r"^(.+): average (.+) likes per post across (\d+) posts\.$"),
     r"\1: average \2 likes per post among \3 analyzed posts (excluding missing like counts)."),
    ("top post insight", re.compile(r"^Top performing (\S+) post: "),
     r"Top performing \1 post among analyzed posts: "),
)


def _1469_case_manifest(case: str, likes_chart: int) -> dict[tuple[str, str, str, str], int]:
    """Declared rewrites for one known-value fixture, by ORIGINAL baseline path.

    Literal, reviewed against the frozen d329eef7 baseline report (never the
    current output). The fixtures differ only in where the likes chart sits:
    the [0, 0] baseline has no followers chart, so its likes chart is first.
    """
    return {
        (case, "Total Likes by Platform", "value", f"report.charts[{likes_chart}].title"): 1,
        (case, "Total Posts (all platforms)", "key",
         "report.metrics[key='Total Posts (all platforms)']"): 1,
        (case, "platform posts metric key", "key", "report.metrics[key='x_twitter — Posts']"): 1,
        (case, "platform posts metric key", "key", "report.metrics[key='instagram — Posts']"): 1,
        (case, "top posts table title", "value", "report.tables[1].title"): 1,
        (case, "top posts table title", "value", "report.tables[2].title"): 1,
        (case, "executive summary", "value", "report.executive_summary"): 1,
        (case, "average likes insight", "value", "report.insights[1]"): 1,
        (case, "average likes insight", "value", "report.insights[3]"): 1,
        (case, "top post insight", "value", "report.insights[2]"): 1,
        (case, "top post insight", "value", "report.insights[4]"): 1,
        (case, "comparison table header", "header", "report.tables[0].headers[3]"): 1,
    }


# Exact expected multiset: 12 occurrences per known-value fixture, 24 in all.
_1469_EXPECTED_REWRITES: Counter = Counter({
    **_1469_case_manifest("known[12, 3]", likes_chart=1),
    **_1469_case_manifest("known[0, 0]", likes_chart=0),
})


def _reword_text(text: str, case: str, kind: str, path: str, observed: Counter) -> str:
    """Reword one baseline string and record (case, rule, kind, path) once."""
    if text in _1469_STRINGS:
        observed[(case, text, kind, path)] += 1
        return _1469_STRINGS[text]
    for name, pattern, replacement in _1469_PATTERNS:
        if pattern.search(text):
            observed[(case, name, kind, path)] += 1
            return pattern.sub(replacement, text)
    return text


def _reword_1469(value: object, case: str, path: str, observed: Counter) -> object:
    """Apply #1469's fixed rewording to a BASELINE report value.

    Returns a reworded copy; the baseline value is not modified. Paths name
    the ORIGINAL baseline location: ``<parent>.<key>`` for a dict value,
    ``<parent>[key=<key>]`` for a dict key, ``<parent>[i]`` for a list item.
    """
    if isinstance(value, dict):
        reworded = {}
        for key, item in value.items():
            new_key = (_reword_text(key, case, "key", f"{path}[key={key!r}]", observed)
                       if isinstance(key, str) else key)
            reworded[new_key] = _reword_1469(item, case, f"{path}.{key}", observed)
        return reworded
    if isinstance(value, list):
        return [_reword_1469(item, case, f"{path}[{i}]", observed) for i, item in enumerate(value)]
    if isinstance(value, str):
        return _reword_text(value, case, "value", path, observed)
    return value


def _reword_table_headers(report: dict[str, Any], case: str, observed: Counter) -> None:
    """#1469 relabels the comparison table's post-count column only."""
    for index, table in enumerate(report.get("tables", [])):
        if table.get("title") == "Platform Comparison" and table["headers"][3] == "Posts":
            table["headers"][3] = f"Posts analyzed (most recent up to {_POSTS_LIMIT})"
            observed[(case, "comparison table header", "header",
                      f"report.tables[{index}].headers[3]")] += 1
            return


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

# The X snapshot date depends on the clock: the baseline labels it with the
# host-local date.today(), the fix with the UTC date. Under a real clock the two
# are usually equal, so a host-local regression matched the baseline and passed,
# and the oracle's own later clock read could disagree with the connector's
# across UTC midnight (#1879). The X snapshot is therefore produced only under
# these fixed clocks: one UTC instant seen from a host whose local date is ahead
# of UTC, then behind it. The expected date comes from the same instant the
# connector saw, never from a second clock read.
X_CLOCKS: tuple[tuple[datetime, timezone], ...] = (
    (datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc), timezone(timedelta(hours=6))),
    (datetime(2026, 2, 1, 0, 0, 1, tzinfo=timezone.utc), timezone(timedelta(hours=-6))),
)
# UTC date of the active X clock; None outside one, so no X date relabel is
# authorized without a fixed clock.
_X_SNAPSHOT_UTC_DATE: date | None = None


def _frozen_clock(instant: datetime, host_tz: timezone) -> tuple[type, type]:
    """``date``/``datetime`` stand-ins for one instant on a host in ``host_tz``.

    ``date.today()`` and naive ``datetime.now()`` give the host-local wall clock;
    ``datetime.now(tz)`` gives the same instant in ``tz``.
    """

    class FrozenDate(date):
        @classmethod
        def today(cls) -> date:
            return instant.astimezone(host_tz).date()

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            if tz is None:
                return instant.astimezone(host_tz).replace(tzinfo=None)
            return instant.astimezone(tz)

        @classmethod
        def today(cls) -> datetime:
            return cls.now()

        @classmethod
        def utcnow(cls) -> datetime:
            return instant.replace(tzinfo=None)

    return FrozenDate, FrozenDateTime


def _is_1444_relabel(old: object, new: object, where: str) -> bool:
    if not (isinstance(old, str) and isinstance(new, str)):
        return False
    if where.startswith("instagram.get_account_insights[") and where.endswith(",'date']"):
        try:
            return new == (date.fromisoformat(old) - timedelta(days=1)).isoformat()
        except ValueError:
            return False
    if where == "x.get_account_insights[0,'date']":
        return _X_SNAPSHOT_UTC_DATE is not None and new == _X_SNAPSHOT_UTC_DATE.isoformat()
    return False


def _compare_x_snapshot_under_fixed_clocks(old: ModuleType, body: object, hits: set[str]) -> int:
    """Compare X ``get_account_insights`` under each of ``X_CLOCKS``.

    Each clock puts the host-local and UTC dates on different days, so the
    baseline (host-local) and a correct current snapshot (UTC) must differ, and
    the UTC relabel must be what reconciles them. A current snapshot that equals
    the baseline is a host-local regression and fails here.
    """
    global _X_SNAPSHOT_UTC_DATE
    allowed = 0
    for instant, host_tz in X_CLOCKS:
        frozen_date, frozen_datetime = _frozen_clock(instant, host_tz)
        assert instant.astimezone(host_tz).date() != instant.date(), (instant, host_tz)
        _RELABELED.discard("x.get_account_insights")
        clock = {"date": frozen_date, "datetime": frozen_datetime}
        with patch.dict(old.__dict__, clock), patch.multiple(x_twitter, **clock):
            with client_for(old, "x", body) as previous, client_for(x_twitter, "x", body) as new:
                before = previous.get_account_insights(START, END)
                after = new.get_account_insights(START, END)
        _X_SNAPSHOT_UTC_DATE = instant.date()
        try:
            allowed += compare(before, after, "x.get_account_insights", hits)
        finally:
            _X_SNAPSHOT_UTC_DATE = None
        assert "x.get_account_insights" in _RELABELED, (
            f"X snapshot at {instant.isoformat()} on a {host_tz} host was not "
            f"relabelled to the UTC date: baseline {before.at[0, 'date']!r}, current "
            f"{after.at[0, 'date']!r}, expected {instant.date().isoformat()!r}"
        )
    return allowed


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
            if _is_count_null_dtype(new[col].dtype) and any(
                hit.startswith(f"{where}[") and hit.endswith(f",{col!r}]") for hit in new_hits
            ):
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
        # An unknown count is a scalar None, numeric NaN or pd.NA; a temporal
        # NaT or a container holding a missing value is not a count (#1880).
        if (_is_zero(old) and _is_scalar_count_unknown(new) and not _is_temporal(new)
                and where in _AUTHORIZED):
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
    x_empty_followers_checked = 0
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
                if platform == "x" and method == "get_account_insights":
                    allowed += _compare_x_snapshot_under_fixed_clocks(old, body, hits)
                    count += 1
                    continue
                with client_for(old, platform, body) as previous, client_for(current, platform, body) as new:
                    before = getattr(previous, method)(*args)
                    after = getattr(new, method)(*args)
                allowed += compare(before, after, f"{platform}.{method}", hits)
                # Identity, not value equality: only the empty-metrics fixture
                # itself selects this check, and the check must run (below).
                if platform == "x" and method == "get_account_info" and body is account_empty:
                    assert after["followers_count"] is None
                    x_empty_followers_checked += 1
                count += 1

    old_report = old_module(social_media_reports)
    observed: Counter = Counter()
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
                # Only the baseline is known to fail, and only on an unknown
                # follower count. Any other TypeError is a new failure: raise it
                # with its traceback instead of recording a placeholder.
                if module is social_media_reports or None not in values:
                    raise
                reports.append("TypeError")
        if None not in values:
            case = f"known{values}"
            baseline = _reword_1469(reports[0], case, "report", observed)
            _reword_table_headers(baseline, case, observed)
            allowed += compare(baseline, reports[1], "report", hits)
        else:
            assert reports[0] == "TypeError"
            assert isinstance(reports[1], dict)
            known = [v for v in values if v is not None]
            expected = str(sum(known)) if known else "unavailable"
            assert reports[1]["metrics"]["Total Followers (all platforms)"]["value"] == expected
            assert reports[1]["metrics"]["x_twitter — Followers"]["value"] == "unavailable"
            assert data[0]["account_info"]["followers_count"] is None
        count += 1
    missing = _1469_EXPECTED_REWRITES - observed
    excess = observed - _1469_EXPECTED_REWRITES
    assert observed == _1469_EXPECTED_REWRITES, (
        "#1469 baseline rewrites differ from the declared manifest; "
        f"missing {sorted(missing.items())}, excess or undeclared {sorted(excess.items())}"
    )
    assert "instagram.get_account_insights" in _RELABELED, (
        "#1444 covered-day relabel of Instagram account insights was not exercised"
    )
    assert x_empty_followers_checked == 1, (
        f"X empty public_metrics null check ran {x_empty_followers_checked} times, expected 1"
    )
    # Each X clock already asserted its own relabel; this guards the wiring.
    assert "x.get_account_insights" in _RELABELED, (
        "#1444 UTC-date relabel of the X snapshot was not exercised"
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
