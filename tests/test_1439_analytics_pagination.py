"""Regression coverage for silent analytics pagination/truncation (#1439)."""

from datetime import date, datetime, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from siege_utilities.analytics import google_analytics as ga
from siege_utilities.analytics.instagram import BASE_URL, InstagramConnector
from siege_utilities.analytics.vista_social import VistaSocialConnector


class FakeResponse:
    status_code = 200
    headers = {}
    content = b"json"

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


def fake_requests(monkeypatch, connector, pages):
    """Exercise the real request helpers, with no network or credentials."""
    calls = []

    def request(method, url, **kwargs):
        assert method == "GET"
        assert len(calls) < len(pages), "Unexpected extra page request"
        calls.append((url, kwargs.get("params") or {}))
        return FakeResponse(pages[len(calls) - 1])

    monkeypatch.setattr(connector._session, "request", request)
    return calls


@pytest.fixture
def instagram():
    with InstagramConnector("test-token", ig_user_id="1", retry_attempts=1) as conn:
        conn._authenticated = True
        yield conn


def post(post_id, timestamp):
    return {"id": post_id, "timestamp": timestamp}


@pytest.mark.parametrize("limit", [None, 2, 3])
def test_instagram_posts_filter_all_pages_across_hosts_and_versions(
    monkeypatch, instagram, limit,
):
    next_page = "https://graph.facebook.com/v23.0/1/media?after=second"
    last_page = "https://graph.instagram.com/v23.0/1/media?after=third"
    calls = fake_requests(monkeypatch, instagram, [
        {"data": [post("a", "2026-01-20T12:00:00+0000")],
         "paging": {"next": next_page}},
        {"data": [post("march", "2026-03-01T00:00:00+0000"),
                  post("old", "2025-06-01T00:00:00+0000")],
         "paging": {"next": last_page}},
        {"data": [post("d", "2026-01-10T00:00:00+0000"),
                  post("e", "2026-01-01T00:00:00+0000"),
                  post("older", "2025-01-01T00:00:00+0000")]},
    ])

    result = instagram.get_posts(date(2026, 1, 1), date(2026, 1, 31), limit=limit)

    assert [url for url, _ in calls] == [f"{BASE_URL}/1/media", next_page, last_page]
    assert result["id"].tolist() == (["a", "d"] if limit == 2 else ["a", "d", "e"])
    assert calls[1][1] == calls[2][1] == {}


@pytest.mark.parametrize("stop", ["limit", "older_page"])
def test_instagram_posts_stop_without_requesting_unneeded_page(monkeypatch, instagram, stop):
    second = [post("b", "2026-01-10T00:00:00+0000"),
              post("c", "2026-01-09T00:00:00+0000")]
    if stop == "older_page":
        second = [post("old", "2025-12-31T23:59:59+0000")]
    calls = fake_requests(monkeypatch, instagram, [
        {"data": [post("a", "2026-01-20T00:00:00+0000")],
         "paging": {"next": "https://graph.instagram.com/v23.0/1/media?after=two"}},
        {"data": second,
         "paging": {"next": "https://graph.instagram.com/v23.0/1/media?after=unused"}},
    ])

    result = instagram.get_posts(
        date(2026, 1, 1), date(2026, 1, 31), limit=2 if stop == "limit" else None,
    )

    assert len(calls) == 2
    assert result["id"].tolist() == (["a", "b"] if stop == "limit" else ["a"])


def test_instagram_posts_only_include_verifiable_dates(monkeypatch, instagram):
    fake_requests(monkeypatch, instagram, [{"data": [
        post("missing", ""), post("invalid", "not-a-date"),
        post("start", "2026-01-01T00:00:00+0000"),
        post("end", "2026-01-31T23:59:59+0000"),
    ]}])

    result = instagram.get_posts(date(2026, 1, 1), date(2026, 1, 31))

    assert result["id"].tolist() == ["start", "end"]


def test_instagram_authenticate_finds_linked_page_after_first_25(monkeypatch):
    next_page = "https://graph.facebook.com/v23.0/me/accounts?after=25"
    with InstagramConnector("test-token", retry_attempts=1) as conn:
        calls = fake_requests(monkeypatch, conn, [
            {"data": [{"id": str(i), "name": str(i)} for i in range(25)],
             "paging": {"next": next_page}},
            {"data": [{"id": "26", "name": "Linked Page",
                       "instagram_business_account": {"id": "linked-ig"}}]},
        ])

        conn.authenticate()

        assert conn.is_connected()
        assert conn._ig_user_id == "linked-ig"
        assert [url for url, _ in calls] == [f"{BASE_URL}/me/accounts", next_page]


def insight(metric, day, value):
    return {"name": metric, "values": [{"end_time": f"{day}T00:00:00+0000", "value": value}]}


def test_instagram_insights_follow_paging_and_combine_metrics(monkeypatch, instagram):
    next_page = "https://graph.instagram.com/v23.0/1/insights?after=two"
    last_page = "https://graph.facebook.com/v23.0/1/insights?after=three"
    calls = fake_requests(monkeypatch, instagram, [
        {"data": [insight("reach", "2026-01-02", 2)], "paging": {"next": next_page}},
        {"data": [insight("impressions", "2026-01-02", 3)], "paging": {"next": last_page}},
        {"data": [insight("reach", "2026-01-01", 1)]},
    ])

    result = instagram.get_account_insights(
        date(2026, 1, 1), date(2026, 1, 2), metrics=["reach", "impressions"],
    )

    assert [url for url, _ in calls] == [f"{BASE_URL}/1/insights", next_page, last_page]
    assert result["date"].tolist() == ["2026-01-01", "2026-01-02"]
    assert result["reach"].tolist() == [1, 2]
    assert result.iloc[1]["impressions"] == 3


def test_instagram_insights_chunk_90_days_and_page_each_chunk(monkeypatch, instagram):
    calls = []

    def request(method, url, **kwargs):
        assert method == "GET"
        assert len(calls) < 6, "Unexpected extra insights request"
        params = kwargs.get("params") or {}
        calls.append((url, params))
        if params:
            assert 0 <= params["until"] - params["since"] <= 30 * 86400
            assert params["metric"] == "reach"
            assert params["period"] == "day"
            day = datetime.fromtimestamp(params["since"], timezone.utc).date().isoformat()
            return FakeResponse({
                "data": [insight("reach", day, 10)],
                "paging": {"next": f"https://graph.instagram.com/v23.0/1/insights?day={day}"},
            })
        day = parse_qs(urlsplit(url).query)["day"][0]
        return FakeResponse({"data": [insight("impressions", day, 20)]})

    monkeypatch.setattr(instagram._session, "request", request)

    result = instagram.get_account_insights(
        date(2026, 1, 1), date(2026, 3, 31), metrics=["reach"],
    )

    chunks = [params for _, params in calls if params]
    assert len(chunks) == 3
    assert len(calls) == 6
    assert chunks[0]["since"] == int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    assert chunks[-1]["until"] == int(datetime(2026, 3, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp())
    assert all(right["since"] == left["until"] + 1 for left, right in zip(chunks, chunks[1:]))
    assert result["date"].tolist() == ["2026-01-01", "2026-01-31", "2026-03-02"]
    assert result["reach"].tolist() == [10, 10, 10]
    assert result["impressions"].tolist() == [20, 20, 20]


@pytest.fixture
def ga_connector(monkeypatch):
    # The optional Google SDK is unnecessary for a deterministic client fake.
    monkeypatch.setattr(ga, "GOOGLE_ANALYTICS_AVAILABLE", True)
    for name in ("RunReportRequest", "DateRange", "Metric", "Dimension"):
        monkeypatch.setattr(ga, name, SimpleNamespace, raising=False)
    return ga.GoogleAnalyticsConnector()


def ga_response(values, total):
    return SimpleNamespace(
        dimension_headers=[SimpleNamespace(name="country")],
        metric_headers=[SimpleNamespace(name="sessions")],
        row_count=total,
        rows=[SimpleNamespace(
            dimension_values=[SimpleNamespace(value=f"country-{value}")],
            metric_values=[SimpleNamespace(value=str(value))],
        ) for value in values],
    )


def test_ga4_pages_by_rows_received_until_row_count(ga_connector):
    offsets = []

    def run_report(request):
        offset = getattr(request, "offset", 0)
        assert offset in (0, 2, 4)
        assert request.property == "properties/123"
        assert request.limit == 3  # The server can return fewer than requested.
        assert request.dimensions[0].name == "country"
        assert request.metrics[0].name == "sessions"
        offsets.append(offset)
        return ga_response(list(range(1, 6))[offset:offset + 2], 5)

    ga_connector.ga4_client = SimpleNamespace(run_report=run_report)
    result = ga_connector.get_ga4_data(
        "123", "2026-01-01", "2026-01-31", ["sessions"], ["country"], row_limit=3,
    )

    assert offsets == [0, 2, 4]
    assert result["country"].tolist() == [f"country-{i}" for i in range(1, 6)]
    assert result["sessions"].tolist() == [1, 2, 3, 4, 5]


def test_ga4_raises_if_paging_stalls_before_advertised_row_count(ga_connector):
    pages = iter([ga_response([1], 2), ga_response([], 2)])
    ga_connector.ga4_client = SimpleNamespace(run_report=lambda request: next(pages))

    with pytest.raises(RuntimeError, match="(?i)(incomplete|truncat|empty page)"):
        ga_connector.get_ga4_data("123", "2026-01-01", "2026-01-31", ["sessions"])


@pytest.mark.parametrize("method,args", [("list_accounts", ()), ("list_profiles", ("a1",))])
@pytest.mark.parametrize("metadata", [
    {"paging": {"next": "https://api.vistasocial.com/v1/accounts?after=two"}},
    {"pagination": {"has_more": True}},
    {"links": {"next": "?page=2"}},
    {"meta": {"total": 2}},
])
def test_vista_lists_signal_more_pages(monkeypatch, method, args, metadata):
    with VistaSocialConnector("test-token", retry_attempts=1) as conn:
        calls = fake_requests(monkeypatch, conn, [
            {"data": [{"id": "first"}], **metadata},
            {"data": [{"id": "second"}]},
        ])

        result = getattr(conn, method)(*args)

        assert isinstance(result, list)
        if len(calls) == 1:
            assert result.has_more is True
            assert result.pagination == metadata
            assert result == [{"id": "first"}]
        else:
            assert result == [{"id": "first"}, {"id": "second"}]


@pytest.mark.parametrize("metadata,has_more", [({}, None), ({"paging": {"next": None}}, False)])
def test_vista_list_distinguishes_unknown_pagination_from_complete(monkeypatch, metadata, has_more):
    with VistaSocialConnector("test-token", retry_attempts=1) as conn:
        fake_requests(monkeypatch, conn, [{"data": [], **metadata}])

        result = conn.list_accounts()

        assert result == []
        assert result.has_more is has_more
