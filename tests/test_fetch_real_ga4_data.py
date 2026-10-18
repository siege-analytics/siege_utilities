"""Offline regression coverage for real GA4 report metrics (#1579)."""

import csv
import socket
import zipfile
from datetime import date, timedelta

import pandas as pd
import pytest
import yaml

from siege_utilities.reporting.examples import google_analytics_report_example as report
from siege_utilities.reporting.idml_export import export_report_idml


def _daily_frame(sessions, bounce_rates, users=None, duration=120):
    return pd.DataFrame({
        'date': [f'2026-01-{i + 1:02d}' for i in range(len(sessions))],
        'sessions': sessions,
        'totalUsers': users if users is not None else sessions,
        'screenPageViews': [count * 2 for count in sessions],
        'bounceRate': bounce_rates,
        'averageSessionDuration': [duration] * len(sessions),
    })


@pytest.fixture
def fetch(monkeypatch):
    import siege_utilities.analytics as analytics
    import siege_utilities.config as config

    def unexpected_io(*args, **kwargs):
        pytest.fail('GA4 regression tests must not use network or credentials')

    monkeypatch.setattr(socket.socket, 'connect', unexpected_io)
    monkeypatch.setitem(config.__dict__, 'get_google_service_account_from_1password', unexpected_io)

    def run(daily=None, prior=None, page_metrics=None, rate=0.45):
        daily = _daily_frame([100], [rate]) if daily is None else daily
        calls = []

        class StubGA4Connector:
            def __init__(self, **kwargs):
                assert kwargs['auth_method'] == 'service_account'

            def get_ga4_data(self, **query):
                calls.append(query)
                dimension = query['dimensions']
                if dimension == ['date']:
                    if sum(call['dimensions'] == ['date'] for call in calls) == 1:
                        return daily.copy()
                    return prior.copy() if prior is not None else pd.DataFrame()
                if dimension == ['sessionDefaultChannelGrouping']:
                    return pd.DataFrame([{'sessionDefaultChannelGrouping': 'Direct',
                                          'sessions': 100, 'totalUsers': 100, 'bounceRate': rate}])
                if dimension == ['deviceCategory']:
                    return pd.DataFrame([{'deviceCategory': 'mobile', 'sessions': 100,
                                          'bounceRate': rate}])
                if dimension == ['pagePath']:
                    return pd.DataFrame([{'pagePath': '/', 'screenPageViews': 200,
                                          'bounceRate': rate, **(page_metrics or {})}])
                if dimension == ['city', 'region', 'country']:
                    return pd.DataFrame([{'city': 'Chicago', 'region': 'Illinois',
                                          'country': 'United States', 'sessions': 100,
                                          'totalUsers': 100}])
                if dimension == ['year']:
                    return pd.DataFrame()
                pytest.fail(f'Unexpected query: {query}')

        monkeypatch.setitem(analytics.__dict__, 'GoogleAnalyticsConnector', StubGA4Connector)
        result = report.fetch_real_ga4_data(
            '123', '2026-01-01', daily['date'].iloc[-1],
            service_account_data={'project_id': 'test-only'},
        )
        return result, calls

    return run


def test_bounce_rate_percentage_with_empty_prior(fetch):
    data, _ = fetch()
    assert f"{data['totals']['avg_bounce_rate']:.1f}%" == '45.0%'
    assert data['daily_data']['bounce_rate'] == [45.0]
    for section in ('traffic_sources', 'devices', 'top_pages'):
        assert data[section][0]['bounce_rate'] == 45.0
    assert data['changes']['sessions'] is None


def test_empty_prior_does_not_fabricate_metrics(fetch):
    data, _ = fetch()
    assert all(value is None for value in data['changes'].values())
    assert not data['prior_period']
    assert data['prior_daily_data']['sessions'] == []
    assert 'unique_views' not in data['top_pages'][0]
    assert 'exit_rate' not in data['top_pages'][0]
    assert data['data_source'] == 'ga4_api'


def test_present_prior_computes_real_changes(fetch):
    data, _ = fetch(prior=_daily_frame([80], [0.50], users=[50], duration=100))
    assert data['prior_period']['avg_bounce_rate'] == 50.0
    assert data['changes'] == {
        'users': 100.0, 'sessions': 25.0, 'bounce_rate': -5.0, 'duration': 20.0,
    }


def test_period_bounce_is_session_weighted(fetch):
    data, _ = fetch(
        daily=_daily_frame([10, 90], [0.90, 0.10]),
        prior=_daily_frame([60, 20], [0.50, 0.10]),
    )
    assert data['totals']['avg_bounce_rate'] == pytest.approx(18.0)
    assert data['prior_period']['avg_bounce_rate'] == pytest.approx(40.0)
    assert data['changes']['bounce_rate'] == pytest.approx(-22.0)


@pytest.mark.parametrize('days', [1, 2])
def test_prior_query_has_same_inclusive_length(fetch, days):
    _, calls = fetch(daily=_daily_frame([100] * days, [0.45] * days))
    prior_query = [call for call in calls if call['dimensions'] == ['date']][1]
    assert prior_query['start_date'] == (date(2026, 1, 1) - timedelta(days=days)).isoformat()
    assert prior_query['end_date'] == '2025-12-31'


@pytest.mark.parametrize('rate', [1.01, 45.0, -0.1, float('nan'), float('inf')])
def test_invalid_api_ratio_is_rejected_without_double_scaling(fetch, rate):
    with pytest.raises(RuntimeError, match='0.*1'):
        fetch(rate=rate)


@pytest.mark.parametrize('rate,expected', [(0, 0.0), (1, 100.0)])
def test_ratio_boundaries(fetch, rate, expected):
    data, _ = fetch(rate=rate)
    assert data['totals']['avg_bounce_rate'] == expected


def test_exit_rate_is_only_used_when_returned(fetch):
    data, _ = fetch(page_metrics={'exitRate': 0.20})
    assert data['top_pages'][0]['exit_rate'] == 20.0
    assert 'unique_views' not in data['top_pages'][0]


def test_zero_prior_denominators_have_no_percentage_change(fetch):
    data, _ = fetch(prior=_daily_frame([0], [0], duration=0))
    assert data['prior_period']['sessions'] == 0
    assert all(value is None for value in data['changes'].values())


def test_correct_scale_drives_insights_and_recommendations(fetch):
    data, _ = fetch(rate=0.65)
    insights = report.generate_insights(data)
    assert any('65.0%' in insight and 'higher than optimal' in insight for insight in insights)
    assert not any('prior period' in insight for insight in insights)
    recommendations = report.generate_recommendations(data)
    assert any('bounce rate' in recommendation.lower() for recommendation in recommendations)


@pytest.fixture
def no_charts(monkeypatch):
    for name in (
        'create_traffic_trend_chart', 'create_traffic_sources_chart',
        'create_device_breakdown_chart', 'create_geo_country_chart',
        'create_geo_region_chart', 'create_geo_city_scatter',
        'create_continent_donut_chart', 'create_period_comparison_chart',
    ):
        monkeypatch.setattr(report, name, lambda *args, **kwargs: None)


def test_design_kit_preserves_missing_comparisons(fetch, tmp_path, no_charts):
    data, _ = fetch()
    report.export_design_kit(data, str(tmp_path))
    with (tmp_path / 'tables/kpi_summary.csv').open() as stream:
        rows = {row[0]: row[1:] for row in csv.reader(stream)}
    assert rows['Sessions'] == ['100', 'N/A']
    assert rows['Avg Bounce Rate'] == ['45.0%', 'N/A']
    assert rows['Pageviews'][1] == 'N/A'
    with (tmp_path / 'tables/top_pages.csv').open() as stream:
        page = list(csv.reader(stream))[1]
    assert page[2] == page[5] == 'N/A'
    assert not (tmp_path / 'tables/period_comparison.csv').exists()
    assert '| Sessions | 100 | N/A |' in (tmp_path / 'text/report_text.md').read_text()
    metadata = yaml.safe_load((tmp_path / 'metadata.yaml').read_text())
    assert all(value is None for value in metadata['changes_vs_prior'].values())


@pytest.mark.parametrize('prior', [None, _daily_frame([0], [0], duration=0)])
def test_pdf_consumers_handle_missing_metrics(fetch, tmp_path, no_charts, prior):
    pytest.importorskip('reportlab')
    data, _ = fetch(prior=prior)
    table = report.create_kpi_dashboard(data)[0]
    assert all(card.change is None for card in table._cellvalues[0])
    assert table._cellvalues[0][2].value == '45.0%'
    page = report.create_top_pages_table(data)[1]
    assert page[2] == page[5] == 'N/A'
    output = tmp_path / 'report.pdf'
    report.generate_ga_report_pdf(data, str(output))
    assert output.read_bytes().startswith(b'%PDF')


def test_design_kit_preserves_real_comparisons(fetch, tmp_path, no_charts):
    data, _ = fetch(prior=_daily_frame([80], [0.50], users=[50], duration=100))
    report.export_design_kit(data, str(tmp_path))
    with (tmp_path / 'tables/period_comparison.csv').open() as stream:
        rows = {row[0]: row[1:] for row in csv.reader(stream)}
    assert rows['Sessions'] == ['100', '80', '+25.0%']
    assert rows['Bounce Rate'] == ['45.0%', '50.0%', '-5.0 pts']
    assert '| Sessions | 100 | +25.0% |' in (tmp_path / 'text/report_text.md').read_text()
    metadata = yaml.safe_load((tmp_path / 'metadata.yaml').read_text())
    assert metadata['changes_vs_prior']['sessions'] == 25.0
    assert metadata['changes_vs_prior']['bounce_rate'] == -5.0


def test_idml_uses_percentage_scale_without_optional_metrics(fetch, tmp_path):
    data, _ = fetch()
    output = export_report_idml(data, str(tmp_path / 'report.idml'))
    with zipfile.ZipFile(output) as archive:
        stories = '\n'.join(archive.read(name).decode() for name in archive.namelist()
                            if name.startswith('Stories/'))
    assert 'Bounce Rate: 45.0%' in stories
    assert '0.5%' not in stories
