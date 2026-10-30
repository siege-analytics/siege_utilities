"""Read-only hostile fixtures. Synthetic sentinels; no real HTTP permitted."""
import logging
from unittest.mock import Mock
from urllib.parse import quote
import pandas as pd
import pytest
import requests
from siege_utilities.connectors._protocol import ConnectorError
from tests.test_1417_crm_retry_idempotency import connector, response

SECRET = 'HOSTILE_SYNTHETIC_ONLY_9a7f'

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(requests.Session, 'send', Mock(side_effect=AssertionError('NETWORK FORBIDDEN')))
    monkeypatch.setattr('time.sleep', Mock())

def configured(provider, secret=SECRET):
    c=connector(provider)
    c._client_secret=c._access_token=secret
    c._session.headers['Authorization']='Bearer '+secret
    c._refresh_token=None
    c._retry_attempts=1
    return c

@pytest.mark.parametrize('secret',[SECRET,'Z7q!9xA'])
def test_salesforce_public_bulk_job_log_suppresses_configured_value(secret,caplog):
    c=configured('salesforce',secret)
    c._session.request=Mock(side_effect=[response(body={'id':secret}),response(body={'state':'UploadComplete'}),response(body={'state':'JobComplete','numberRecordsProcessed':1,'numberRecordsFailed':0})])
    c._session.put=Mock(return_value=response(201))
    csv=response();csv._content=b'sf__Id,sf__Created\n001,true\n'
    c._session.get=Mock(return_value=csv)
    caplog.set_level(logging.INFO)
    result=c.bulk_insert('contacts',pd.DataFrame([{'name':'ordinary'}]))
    assert result.ok and result.created_ids==['001']
    assert caplog.records
    assert secret not in caplog.text

@pytest.mark.parametrize('operation',['create_association','remove_association','merge_contacts'])
@pytest.mark.parametrize('secret',[SECRET,'Z7q!9xA'])
def test_hubspot_public_id_logs_suppress_configured_value(operation,secret,caplog):
    c=configured('hubspot',secret)
    c._session.request=Mock(return_value=response(204))
    caplog.set_level(logging.INFO)
    if operation=='merge_contacts':c.merge_contacts('primary',secret)
    else:getattr(c,operation)('contacts',secret,'companies','ordinary')
    assert caplog.records
    assert secret not in caplog.text

@pytest.mark.parametrize('provider',['salesforce','hubspot','zoho','dynamics'])
def test_mixed_percent_hex_case_path_is_redacted(provider):
    secret='HOSTILE_SYNTHETIC_ONLY /+Ω_end9f2a'
    c=configured(provider,secret)
    encoded=quote(secret,safe='')
    encoded=encoded.replace('%2F','%2f') # other triplets remain uppercase: same decoded credential
    c._session.request=Mock(return_value=response(404))
    with pytest.raises(ConnectorError) as caught:c.request('POST','/records/'+encoded)
    assert encoded not in str(caught.value)
