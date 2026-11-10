"""R-1812-3 oracle for the social fidelity audit comparator (#1812).

The audit in scripts/check_social_review_fidelity.py must authorize a
baseline-zero -> current-null only at the explicit omitted-post cells and
compare everything else strictly (type, timezone, index name). These checks
encode the reviewer's adversarial seeds (review-1812-154e2f0e.md): the prior
comparator false-greened the timezone relabel, the 0 -> False change, the
index-name change, a non-count zero -> null, and the counterbalanced swap.

The script is loaded by path (it is not an importable package module); the
real `audit()` runs the baseline-vs-current comparison offline against the
frozen d329eef7 sources in tests/fixtures/social_baseline_d329eef7/.
"""
import importlib.util
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_social_review_fidelity.py"
_spec = importlib.util.spec_from_file_location("check_social_review_fidelity", _SCRIPT)
fidelity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fidelity)

IG_OMITTED = "instagram._posts_to_dataframe.omitted"
IG_POPULATED = "instagram._posts_to_dataframe.populated"


def _frame(col, value):
    return pd.DataFrame({col: [value]})


def test_unmutated_audit_is_green():
    # The real baseline-vs-current audit still passes: exactly the eight
    # authorized omitted-post nulls, nothing else. This is the green-at-head
    # control; it fails if the explicit locations or counts are wrong.
    fidelity.audit()


def test_authorized_set_has_eight_locations():
    assert len(fidelity._AUTHORIZED) == 8


def test_authorized_zero_to_null_is_counted_and_recorded():
    hits = set()
    n = fidelity.compare(_frame("like_count", 0), _frame("like_count", None), IG_OMITTED, hits)
    assert n == 1
    assert hits == {f"{IG_OMITTED}[0,'like_count']"}


def test_zero_to_null_outside_authorized_fixture_is_rejected():
    # The populated-measured-0-nulled half of the counterbalanced swap.
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("like_count", 0), _frame("like_count", None), IG_POPULATED, set())


def test_null_to_zero_is_rejected_even_at_authorized_location():
    # The omitted-null-fabricated-to-0 half: authorized cells permit zero->null,
    # never null->zero, so the swap cannot net to the expected total.
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("like_count", None), _frame("like_count", 0), IG_OMITTED, set())


def test_non_count_zero_to_null_is_rejected():
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("engagement_rate", 0.0), _frame("engagement_rate", None), IG_OMITTED, set())


def test_same_instant_timezone_relabel_is_rejected():
    utc = pd.Timestamp("2026-01-02T00:00:00Z")
    with pytest.raises(AssertionError):
        fidelity.compare(
            _frame("published_at", utc),
            _frame("published_at", utc.tz_convert("America/Chicago")),
            IG_POPULATED, set(),
        )


def test_zero_to_false_type_change_is_rejected():
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("like_count", 0), _frame("like_count", False), IG_POPULATED, set())


def test_index_name_change_is_rejected():
    old = _frame("like_count", 1)
    new = _frame("like_count", 1)
    new.index.name = "relabelled"
    with pytest.raises(AssertionError):
        fidelity.compare(old, new, IG_POPULATED, set())


def test_lost_authorized_null_is_not_recorded():
    # If the omitted fix is lost (cell stays 0), the location is never hit, so
    # audit()'s `hits == _AUTHORIZED` assertion fails -- a compensating change
    # cannot mask the lost null.
    hits = set()
    fidelity.compare(_frame("like_count", 0), _frame("like_count", 0), IG_OMITTED, hits)
    assert hits == set()
    assert fidelity._AUTHORIZED - hits


def test_changed_known_count_is_rejected():
    with pytest.raises(AssertionError):
        fidelity.compare(_frame("like_count", 4), _frame("like_count", 5), IG_POPULATED, set())


def test_removed_row_is_rejected():
    old = pd.DataFrame({"like_count": [1, 2]})
    new = pd.DataFrame({"like_count": [1]})
    with pytest.raises(AssertionError):
        fidelity.compare(old, new, IG_POPULATED, set())


# The exact-head review of b7199b4e found four mutations of real current
# output that the real audit still certified. Each test applies one of them to
# the actual current Instagram converter output inside the complete audit;
# the audit must now fail.
def _mutate_current_instagram(monkeypatch, mutate):
    from siege_utilities.analytics import instagram

    real = instagram.InstagramConnector._posts_to_dataframe

    def mutated(posts):
        frame = real(posts)
        label = "populated" if posts and "caption" in posts[0] else "omitted" if posts else "empty"
        return mutate(label, frame.copy(deep=True))

    monkeypatch.setattr(instagram.InstagramConnector, "_posts_to_dataframe", staticmethod(mutated))


def _set_omitted_media_url_to_na(label, frame):
    if label == "omitted":
        frame["media_url"] = pd.Series([pd.NA], index=frame.index, dtype=object)
    return frame


def _set_omitted_published_at_to_none(label, frame):
    if label == "omitted":
        frame["published_at"] = pd.Series([None], index=frame.index, dtype=object)
    return frame


def _make_populated_index_float(label, frame):
    if label == "populated":
        frame.index = pd.Index([float(value) for value in frame.index])
    return frame


def _name_populated_column_axis(label, frame):
    if label == "populated":
        frame.columns.name = "changed_column_axis"
    return frame


@pytest.mark.parametrize("mutate", [
    _set_omitted_media_url_to_na,
    _set_omitted_published_at_to_none,
    _make_populated_index_float,
    _name_populated_column_axis,
])
def test_review_seed_is_rejected_by_the_real_audit(monkeypatch, mutate):
    _mutate_current_instagram(monkeypatch, mutate)
    with pytest.raises(AssertionError):
        fidelity.audit()


def _make_populated_published_at_object(label, frame):
    # Same Timestamp values, but the column loses its tz-aware datetime dtype.
    if label == "populated":
        frame["published_at"] = frame["published_at"].astype(object)
    return frame


def test_column_dtype_change_with_equal_cells_is_rejected(monkeypatch):
    _mutate_current_instagram(monkeypatch, _make_populated_published_at_object)
    with pytest.raises(AssertionError, match="unexpected dtype change"):
        fidelity.audit()


def test_dtype_change_is_allowed_only_in_an_authorized_null_column():
    where = IG_OMITTED
    old = pd.DataFrame({"like_count": [0], "id": ["1"]})
    new = pd.DataFrame({"like_count": [None], "id": ["1"]})
    hits = set()
    assert fidelity.compare(old, new, where, hits) == 1
    assert old["like_count"].dtype != new["like_count"].dtype
    stamps = pd.Series(pd.to_datetime(["2026-01-02"], utc=True))
    with pytest.raises(AssertionError, match="unexpected dtype change"):
        fidelity.compare(
            pd.DataFrame({"published_at": stamps}),
            pd.DataFrame({"published_at": stamps.astype(object)}),
            IG_POPULATED, set(),
        )


def test_seed_controls_leave_the_audit_green(monkeypatch):
    # The wrapper alone (no mutation) keeps the real audit green, so a seed
    # failure is caused by its mutation and not by the wrapping.
    _mutate_current_instagram(monkeypatch, lambda label, frame: frame)
    fidelity.audit()


def test_frozen_baseline_matches_the_reviewed_commit():
    for path, blob in fidelity.BASELINE_BLOBS.items():
        frozen = fidelity.FROZEN / (Path(path).name + ".txt")
        assert fidelity.git_blob_id(frozen.read_bytes()) == blob, path


# #1879: the X snapshot date under host-local / UTC clocks on different days.
# These tests set the clocks from outside the helper (baseline module, current
# connector, oracle), so they describe the same scenarios for any helper.
LOCAL_AHEAD = (datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc), timezone(timedelta(hours=6)))
LOCAL_BEHIND = (datetime(2026, 2, 1, 0, 0, 1, tzinfo=timezone.utc), timezone(timedelta(hours=-6)))


def _clock_classes(instant: datetime, host_tz: timezone) -> tuple[type, type]:
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

    return FrozenDate, FrozenDateTime


def _set_clocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    baseline: tuple[datetime, timezone],
    connector: tuple[datetime, timezone],
    oracle: tuple[datetime, timezone],
) -> None:
    """Freeze the X baseline module, the current X connector and the oracle."""
    from siege_utilities.analytics import x_twitter

    base_date, base_datetime = _clock_classes(*baseline)
    real_old_module = fidelity.old_module

    def old_module_with_clock(module: Any) -> Any:
        old = real_old_module(module)
        if module is x_twitter:
            old.date, old.datetime = base_date, base_datetime
        return old

    monkeypatch.setattr(fidelity, "old_module", old_module_with_clock)
    conn_date, conn_datetime = _clock_classes(*connector)
    monkeypatch.setattr(x_twitter, "date", conn_date)
    monkeypatch.setattr(x_twitter, "datetime", conn_datetime)
    monkeypatch.setattr(fidelity, "datetime", _clock_classes(*oracle)[1])


def _mutate_current_x_snapshot_date(monkeypatch: pytest.MonkeyPatch, label: Callable[[], str]) -> None:
    from siege_utilities.analytics import x_twitter

    real = x_twitter.XTwitterConnector.get_account_insights

    def mutated(self: Any, *args: Any, **kwargs: Any) -> pd.DataFrame:
        frame = real(self, *args, **kwargs)
        frame.loc[0, "date"] = label()
        return frame

    monkeypatch.setattr(x_twitter.XTwitterConnector, "get_account_insights", mutated)


def test_x_wrong_host_local_snapshot_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # #1879 (a): host-local Jan 31, UTC Feb 1 00:00:01Z. A current producer that
    # labels the snapshot Jan 31 equals the host-local baseline; it must fail.
    _set_clocks(monkeypatch, baseline=LOCAL_BEHIND, connector=LOCAL_BEHIND, oracle=LOCAL_BEHIND)
    _mutate_current_x_snapshot_date(monkeypatch, lambda: "2026-01-31")
    with pytest.raises(AssertionError):
        fidelity.audit()


def test_x_correct_snapshot_across_utc_midnight_is_green(monkeypatch: pytest.MonkeyPatch) -> None:
    # #1879 (b): the connector reads Jan 31 23:59:59Z (correct date Jan 31) on a
    # host already at Feb 1; the oracle compares at Feb 1 00:00:01Z. The correct
    # source must stay green.
    _set_clocks(monkeypatch, baseline=LOCAL_AHEAD, connector=LOCAL_AHEAD, oracle=LOCAL_BEHIND)
    fidelity.audit()
    assert {"instagram.get_account_insights", "x.get_account_insights"} <= fidelity._RELABELED


def _host_local_today() -> str:
    from siege_utilities.analytics import x_twitter

    return x_twitter.date.today().isoformat()


def _host_local_naive_now() -> str:
    from siege_utilities.analytics import x_twitter

    return x_twitter.datetime.now().date().isoformat()


@pytest.mark.parametrize("host_local_label", [_host_local_today, _host_local_naive_now],
                         ids=["date.today", "naive-datetime.now"])
def test_x_host_local_producer_is_rejected(
    monkeypatch: pytest.MonkeyPatch, host_local_label: Callable[[], str],
) -> None:
    # A current producer that reverts to the host-local date, through either
    # stdlib entry point, always matches the host-local baseline.
    _mutate_current_x_snapshot_date(monkeypatch, host_local_label)
    with pytest.raises(AssertionError):
        fidelity.audit()


def test_x_date_relabel_needs_a_fixed_clock() -> None:
    # Outside a fixed clock no X date difference is authorized, not even one that
    # happens to equal today's UTC date.
    today_utc = datetime.now(timezone.utc).date()
    old = pd.DataFrame({"date": [(today_utc - timedelta(days=1)).isoformat()]})
    new = pd.DataFrame({"date": [today_utc.isoformat()]})
    with pytest.raises(AssertionError):
        fidelity.compare(old, new, "x.get_account_insights", set())


@pytest.mark.parametrize("instant,offset", [
    (datetime(2026, 1, 31, 23, 30, tzinfo=timezone.utc), timedelta(hours=1)),
    (datetime(2026, 1, 31, 23, 30, tzinfo=timezone.utc), timedelta(hours=5, minutes=30)),
    (datetime(2026, 1, 31, 23, 30, tzinfo=timezone.utc), timedelta(hours=14)),
    (datetime(2026, 2, 1, 0, 30, tzinfo=timezone.utc), timedelta(hours=-1)),
    (datetime(2026, 2, 1, 0, 30, tzinfo=timezone.utc), timedelta(hours=-12)),
])
def test_correct_x_snapshot_is_green_for_any_divergent_host(
    monkeypatch: pytest.MonkeyPatch, instant: datetime, offset: timedelta,
) -> None:
    monkeypatch.setattr(fidelity, "X_CLOCKS", ((instant, timezone(offset)),))
    fidelity.audit()


def test_x_clock_without_a_date_divergence_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    # A clock on which host-local and UTC dates agree cannot tell a UTC producer
    # from a host-local one, so the helper refuses it rather than passing.
    monkeypatch.setattr(fidelity, "X_CLOCKS", ((LOCAL_AHEAD[0], timezone.utc),))
    with pytest.raises(AssertionError):
        fidelity.audit()


def test_instagram_two_day_shift_is_still_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only the exact one-day covered-day relabel is authorized for Instagram.
    from siege_utilities.analytics import instagram

    real = instagram.InstagramConnector.get_account_insights

    def shifted(self: Any, *args: Any, **kwargs: Any) -> pd.DataFrame:
        frame = real(self, *args, **kwargs)
        frame["date"] = [(date.fromisoformat(d) - timedelta(days=1)).isoformat() for d in frame["date"]]
        return frame

    monkeypatch.setattr(instagram.InstagramConnector, "get_account_insights", shifted)
    with pytest.raises(AssertionError, match="unexpected value diff"):
        fidelity.audit()
