"""Independent R-1780 calendar-day tests; no connector/credential access."""
import contextlib
import io
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

def process(frame):
    nb = json.loads((ROOT / 'notebooks/analytics/01_connectors.ipynb').read_text())
    code = next(c['source'] for c in nb['cells'] if c['id'] == 'c5')
    ns = {'ga_daily': frame, 'snowflake_daily': None}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(''.join(code), ns)
    return ns

@pytest.mark.parametrize('calendar_days', [1, 6, 7])
def test_counts_calendar_dates_not_timestamps(calendar_days):
    dates = []
    for monday in ['2026-09-28', '2026-10-05']:
        start = pd.Timestamp(monday)
        observed = list(pd.date_range(start, periods=calendar_days, freq='D'))
        # Seven DISTINCT instants, but only 1 or6 distinct dates in partial cases.
        observed += [start + pd.Timedelta(hours=i + 1) for i in range(7 - calendar_days)]
        dates.extend(observed)
    ns = process(pd.DataFrame({'date': dates, 'sessions': [100]*7 + [200]*7}))
    summary = ns['summary']
    assert summary['observed_days'].tolist() == [calendar_days, calendar_days], summary
    wow = pd.to_numeric(summary['WoW change %'], errors='coerce')
    if calendar_days < 7:
        assert wow.isna().all(), summary
    else:
        assert wow.iloc[-1] == 100.0, summary

@pytest.mark.parametrize('day_counts', [(6, 7), (7, 6), (0, 7), (7, 0)])
def test_partial_or_absent_week_withholds(day_counts):
    dates=[]
    for start, count in zip(['2026-09-28', '2026-10-05'], day_counts):
        dates.extend(pd.date_range(start, periods=count, freq='D'))
    summary=process(pd.DataFrame({'date':dates,'sessions':[100]*len(dates)}))['summary']
    assert pd.to_numeric(summary['WoW change %'], errors='coerce').isna().all(), summary
