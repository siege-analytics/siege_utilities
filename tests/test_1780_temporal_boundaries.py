"""Execute actual c5 with calendar/DST neighbours; no connectors or credentials."""
import contextlib
import io
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1]

def process(frame):
    before=frame.copy(deep=True)
    nb=json.loads((ROOT/'notebooks/analytics/01_connectors.ipynb').read_text())
    code=next(c['source'] for c in nb['cells'] if c['id']=='c5')
    ns={'ga_daily':frame,'snowflake_daily':None}
    try:
        with contextlib.redirect_stdout(io.StringIO()):exec(''.join(code),ns)
    finally:pd.testing.assert_frame_equal(frame,before)
    return ns

def checked(dates,values,days,change=None):
    ns=process(pd.DataFrame({'date':dates,'sessions':values}))
    summary=ns['summary']
    assert summary['observed_days'].tolist()==days
    numeric=pd.to_numeric(summary['WoW change %'],errors='coerce')
    if change is not None:assert numeric.iloc[-1]==change
    return ns

@pytest.mark.parametrize('tz,start',[('UTC','2026-02-23'),('America/Chicago','2026-02-23'),('America/Chicago','2026-10-19')])
def test_full_local_weeks_near_midnight_and_us_dst(tz,start):
    days=pd.date_range(start,periods=14,freq='D')
    dates=[pd.Timestamp(f'{d.date()} {clock}').tz_localize(tz) for d in days for clock in ['00:05','23:55']]
    checked(dates,[v for i in range(14) for v in [100 if i<7 else 200]*2],[7,7],100.0)

@pytest.mark.parametrize('tz',['Pacific/Kiritimati','America/Los_Angeles'])
def test_local_six_dates_do_not_become_seven_utc_dates(tz):
    dates=[]
    for monday in ['2026-09-28','2026-10-05']:
        for day in pd.date_range(monday,periods=6,freq='D'):
            dates.extend(pd.Timestamp(f'{day.date()} {clock}').tz_localize(tz) for clock in ['00:05','23:55'])
    ns=checked(dates,[100]*24,[6,6])
    assert pd.to_numeric(ns['summary']['WoW change %'],errors='coerce').isna().all()

@pytest.mark.parametrize('tz',[None,'UTC','America/Chicago'])
def test_week_crossing_new_year(tz):
    dates=pd.date_range('2026-12-21 12:00',periods=14,freq='D',tz=tz)
    ns=checked(dates,[100]*7+[200]*7,[7,7],100.0)
    assert ns['summary'].index.strftime('%Y-%m-%d').tolist()==['2026-12-21','2026-12-28']

@pytest.mark.parametrize('zeros',['one_day_each_week','first_week','second_week'])
def test_zero_measurements_are_still_observed_days(zeros):
    values=[100]*7+[200]*7
    expected=None
    if zeros=='one_day_each_week':values[3]=values[10]=0;expected=100.0
    if zeros=='first_week':values[:7]=[0]*7
    if zeros=='second_week':values[7:]=[0]*7;expected=-100.0
    ns=checked(pd.date_range('2026-09-28 12:00',periods=14,freq='D'),values,[7,7],expected)
    if zeros=='first_week':
        assert ns['summary']['weekly_sessions'].tolist()==[0,1400]
        # Observe inherited denominator-zero behaviour; do not bless its display contract.
        assert np.isinf(ns['summary']['WoW change %'].iloc[-1])

@pytest.mark.parametrize('tz,start',[
    ('America/Havana','2026-10-19'),
    ('America/Santiago','2026-08-24'),
    ('America/Sao_Paulo','2018-10-22'),
])
def test_valid_local_noons_do_not_require_localizable_midnight(tz,start):
    # Valid noons include a day whose midnight is ambiguous or nonexistent.
    # Creating these inputs never localizes the problematic midnight.
    dates=pd.date_range(start+' 12:00',periods=14,freq='D',tz=tz)
    checked(dates,[100]*7+[200]*7,[7,7],100.0)

def test_repeated_dst_hour_is_one_calendar_date():
    first=pd.to_datetime(['2026-11-01T05:05Z','2026-11-01T06:00Z','2026-11-01T06:30Z','2026-11-01T07:00Z','2026-11-01T07:30Z','2026-11-01T18:00Z','2026-11-02T05:55Z']).tz_convert('America/Chicago')
    second=pd.to_datetime(['2026-11-08 '+clock for clock in ['00:05','01:00','01:30','06:00','12:00','18:00','23:55']]).tz_localize('America/Chicago')
    ns=checked(first.append(second),[100]*7+[200]*7,[1,1])
    assert pd.to_numeric(ns['summary']['WoW change %'],errors='coerce').isna().all()
