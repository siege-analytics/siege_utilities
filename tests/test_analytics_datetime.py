"""Regression tests for analytics dates and timezones (#1444)."""

import time
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from siege_utilities.analytics import pipeline
from siege_utilities.analytics.instagram import InstagramConnector
from siege_utilities.analytics.pipeline import PipelineAnalyzer, PipelineItem
from siege_utilities.analytics.x_twitter import XTwitterConnector


@pytest.fixture
def instagram(monkeypatch):
    """Exercise the connector with all HTTP requests intercepted."""
    response = Mock(status_code=200)
    response.json.return_value = {"data": []}
    request = Mock(return_value=response)
    with InstagramConnector("test-token", ig_user_id="123") as connector:
        monkeypatch.setattr(connector._session, "request", request)
        connector.authenticate()
        request.reset_mock()
        yield connector, request, response


@pytest.fixture(params=["America/Chicago", "Pacific/Auckland"])
def host_timezone(request, monkeypatch):
    """Restore the process timezone even after an assertion fails."""
    if not hasattr(time, "tzset"):
        pytest.skip("Changing the host timezone requires time.tzset")
    try:
        with monkeypatch.context() as context:
            context.setenv("TZ", request.param)
            time.tzset()
            yield
    finally:
        time.tzset()


@pytest.mark.parametrize("month", [1, 7])
def test_instagram_insight_window_is_utc(instagram, host_timezone, month):
    connector, request, _ = instagram
    connector.get_account_insights(date(2026, month, 1), date(2026, month, 2))

    request.assert_called_once()
    params = request.call_args.kwargs["params"]
    assert params["period"] == "day"
    assert params["since"] == int(
        datetime(2026, month, 1, tzinfo=timezone.utc).timestamp()
    )
    assert params["until"] == int(
        datetime(2026, month, 3, tzinfo=timezone.utc).timestamp()
    ) - 1


@pytest.mark.parametrize(
    "end_time, covered_day",
    [
        ("2026-01-02T00:00:00+0000", "2026-01-01"),
        ("2026-01-02T08:00:00+0000", "2026-01-01"),
        ("2026-01-02T00:00:00+05:30", "2026-01-01"),
        ("2026-01-01T00:00:00-08:00", "2025-12-31"),
        ("2024-03-01T00:00:00Z", "2024-02-29"),
        ("2026-03-01T00:00:00Z", "2026-02-28"),
    ],
)
def test_instagram_insights_use_covered_day(instagram, end_time, covered_day):
    connector, _, response = instagram
    response.json.return_value = {
        "data": [
            {
                "name": "reach",
                "period": "day",
                "values": [{"end_time": end_time, "value": 7}],
            },
            {
                "name": "profile_views",
                "period": "day",
                "values": [{"end_time": end_time, "value": 3}],
            },
        ],
    }
    day = date.fromisoformat(covered_day)
    frame = connector.get_account_insights(
        day, day, ["reach", "profile_views"],
    )

    assert list(frame.columns) == ["date", "reach", "profile_views"]
    assert frame.to_dict("records") == [
        {"date": covered_day, "reach": 7, "profile_views": 3},
    ]


@pytest.fixture
def utc_now(monkeypatch):
    """Freeze now while preserving datetime.now's naive/aware semantics."""
    reference = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)
    clock = Mock(wraps=datetime)
    clock.now.side_effect = lambda tz=None: (
        reference.astimezone(tz) if tz is not None
        else reference.astimezone().replace(tzinfo=None)
    )
    monkeypatch.setattr(pipeline, "datetime", clock)
    return reference, clock.now


def test_pipeline_default_as_of_accepts_aware_timestamps(utc_now):
    reference, now = utc_now
    entered = (reference - timedelta(days=5)).astimezone(
        timezone(timedelta(hours=-8))
    )
    item = PipelineItem("aware", "lead", 100, entered)

    report = PipelineAnalyzer(["lead"]).analyze([item])

    now.assert_called_once_with(timezone.utc)
    assert report.velocity[0].avg_days == 5.0
    assert report.velocity[0].max_days == 5.0
    assert item.entered_stage is entered


@pytest.mark.parametrize("as_of_kind", ["default", "naive", "utc", "offset"])
def test_pipeline_mixed_timestamps_name_offending_items(utc_now, as_of_kind):
    reference, _ = utc_now
    offset = timezone(timedelta(hours=5, minutes=30))
    as_of = {
        "default": None,
        "naive": reference.replace(tzinfo=None),
        "utc": reference,
        "offset": reference.astimezone(offset),
    }[as_of_kind]
    items = [
        PipelineItem("naive", "lead", 100,
                     (reference - timedelta(days=3)).replace(tzinfo=None)),
        PipelineItem("offset", "lead", 100,
                     (reference - timedelta(days=5)).astimezone(offset)),
        PipelineItem("aging", "lead", 100, reference - timedelta(days=20)),
        PipelineItem("future", "lead", 100, reference + timedelta(days=2)),
        PipelineItem("missing", "lead", 100),
    ]

    with pytest.raises(ValueError, match="naive.*aware") as exc_info:
        PipelineAnalyzer(["lead"]).analyze(items, as_of=as_of)

    for item in items[:-1]:
        assert repr(item.item_id) in str(exc_info.value)
    assert "missing" not in str(exc_info.value)
    assert items[0].entered_stage.tzinfo is None


@pytest.mark.parametrize("as_of_kind", ["default", "utc", "offset"])
def test_pipeline_aware_timestamps_are_normalized_to_utc(utc_now, as_of_kind):
    reference, _ = utc_now
    offset = timezone(timedelta(hours=5, minutes=30))
    as_of = {
        "default": None,
        "utc": reference,
        "offset": reference.astimezone(offset),
    }[as_of_kind]
    entered = (reference - timedelta(days=5)).astimezone(offset)
    items = [
        PipelineItem("utc", "lead", 100, reference - timedelta(days=3)),
        PipelineItem("offset", "lead", 100, entered),
        PipelineItem("aging", "lead", 100, reference - timedelta(days=20)),
        PipelineItem("future", "lead", 100, reference + timedelta(days=2)),
        PipelineItem("missing", "lead", 100),
    ]

    report = PipelineAnalyzer(["lead"]).analyze(items, as_of=as_of)

    assert len(report.velocity) == 1
    velocity = report.velocity[0]
    assert velocity.stage == "lead"
    assert velocity.avg_days == 7.0
    assert velocity.max_days == 20.0
    assert velocity.aging_items == ["aging"]
    assert items[1].entered_stage is entered


@pytest.mark.parametrize("as_of_kind", ["default", "naive"])
def test_pipeline_naive_only_input_uses_local_time(
    utc_now, host_timezone, as_of_kind,
):
    reference, now = utc_now
    local_reference = reference.astimezone().replace(tzinfo=None)
    item = PipelineItem(
        "naive", "lead", 100, local_reference - timedelta(days=2),
    )
    as_of = local_reference if as_of_kind == "naive" else None

    report = PipelineAnalyzer(["lead"]).analyze([item], as_of=as_of)

    if as_of is None:
        now.assert_called_once_with()
    else:
        now.assert_not_called()
    assert report.velocity[0].avg_days == 2.0
    assert report.velocity[0].max_days == 2.0
    assert item.entered_stage.tzinfo is None


@pytest.mark.parametrize("as_of_is_aware", [False, True])
def test_pipeline_rejects_as_of_awareness_mismatch(as_of_is_aware):
    reference = datetime(2026, 1, 10, 12)
    if as_of_is_aware:
        as_of = reference.replace(tzinfo=timezone.utc)
        entered = reference - timedelta(days=2)
    else:
        as_of = reference
        entered = (reference - timedelta(days=2)).replace(tzinfo=timezone.utc)
    items = [
        PipelineItem("first", "lead", 100, entered),
        PipelineItem("missing", "lead", 100),
        PipelineItem("second", "lead", 100, entered),
    ]

    with pytest.raises(ValueError, match="as_of") as exc_info:
        PipelineAnalyzer(["lead"]).analyze(items, as_of=as_of)

    message = str(exc_info.value)
    assert "naive" in message
    assert "aware" in message
    assert "'first'" in message
    assert "'second'" in message
    assert "missing" not in message


def test_pipeline_velocity_measures_elapsed_time_across_dst():
    chicago = ZoneInfo("America/Chicago")
    # The spring-forward interval is 27 elapsed hours, not 28 wall-clock hours.
    entered = datetime(2026, 3, 7, 12, tzinfo=chicago)
    as_of = datetime(2026, 3, 8, 16, tzinfo=chicago)
    item = PipelineItem("dst", "lead", 100, entered)

    report = PipelineAnalyzer(["lead"]).analyze([item], as_of=as_of)

    assert report.velocity[0].avg_days == 1.1
    assert report.velocity[0].max_days == 1.1


@pytest.fixture
def host_tz(monkeypatch):
    def _set(name):
        monkeypatch.setenv("TZ", name)
        time.tzset()
    yield _set
    monkeypatch.undo()
    time.tzset()


def test_pipeline_rejects_mixed_naive_and_aware_inputs():
    items = [
        PipelineItem("aware", "lead", 1.0, datetime(2026, 1, 1, tzinfo=timezone.utc)),
        PipelineItem("naive", "lead", 1.0, datetime(2026, 1, 1)),
    ]
    with pytest.raises(ValueError, match="naive"):
        PipelineAnalyzer(["lead"]).analyze(
            items, as_of=datetime(2026, 1, 3, tzinfo=timezone.utc))


def test_pipeline_naive_local_inputs_keep_their_age(host_tz):
    host_tz("America/Chicago")
    entered = datetime.now() - timedelta(days=2)   # naive host-local, as v4.0.0 callers pass
    report = PipelineAnalyzer(["lead"]).analyze([PipelineItem("n", "lead", 1.0, entered)])
    assert report.velocity[0].avg_days == 2.0


@pytest.mark.parametrize("tz", ["Etc/GMT-14", "Etc/GMT+12"])
def test_x_snapshot_is_labelled_with_utc_date(host_tz, monkeypatch, tz):
    # UTC+14 and UTC-12 together disagree with the UTC date at every hour of the day.
    host_tz(tz)
    conn = XTwitterConnector("token", user_id="1")
    monkeypatch.setattr(conn, "_ensure_connected", lambda: None)
    monkeypatch.setattr(conn, "get_account_info", lambda: {"followers_count": 1})
    before = datetime.now(timezone.utc).date()
    frame = conn.get_account_insights(date(2026, 1, 1), date(2026, 1, 2), ["followers_count"])
    after = datetime.now(timezone.utc).date()
    assert frame.loc[0, "date"] in {str(before), str(after)}
