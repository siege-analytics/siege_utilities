"""New adapter-surface probes: synthetic credentials, no real transport."""
import logging
from unittest.mock import Mock

import pytest
import requests
from siege_utilities.connectors._protocol import ConnectorError, _SECRET_COLLECTION_FAILED
from siege_utilities.connectors.salesforce import SalesforceConnector
from tests.test_1417_crm_retry_idempotency import connector, response

LONG='REVIEW_ONLY_LONG_CONFIGURED_SECRET_7a4c'
SHORT='Z7q!9xA'
NEW='REVIEW_ONLY_ROTATED_CONFIGURED_SECRET_81bc'

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(requests.Session,'send',Mock(side_effect=AssertionError('NO NETWORK')))
    monkeypatch.setattr('time.sleep',Mock())

def configured(provider,secret=LONG):
    c=connector(provider)
    c._access_token=c._client_secret=secret
    c._refresh_token=None
    c._session.headers['Authorization']='Bearer '+secret
    c._retry_attempts=1
    return c

@pytest.mark.parametrize('flow',['code','refresh','password'])
@pytest.mark.parametrize('secret',[LONG,SHORT])
def test_salesforce_upstream_instance_success_log_is_suppressed(flow,secret,caplog):
    c=configured('salesforce',secret)
    c._session.post=Mock(return_value=response(body={
        'access_token':'REVIEW_NEW_ACCESS_TOKEN_LONG_6c9a',
        'refresh_token':'REVIEW_NEW_REFRESH_TOKEN_LONG_b17c',
        'instance_url':'https://instance.invalid/'+secret,
    }))
    caplog.set_level(logging.INFO);caplog.clear()
    if flow=='code':c.authenticate_with_code('synthetic-code','https://callback.invalid')
    elif flow=='refresh':
        c._refresh_token='REVIEW_OLD_REFRESH_TOKEN_LONG_9fac';c.refresh_access_token()
    else:
        c._username='ordinary-user';c._password='REVIEW_PASSWORD_LONG_3f2c';c.authenticate()
    assert c.is_connected()
    assert caplog.records
    assert secret not in caplog.text

class HeadersFailGet(dict):
    def get(self,*args,**kwargs):raise RuntimeError('synthetic collector failure')

def test_collector_failure_cannot_fall_back_to_key_only_logging(caplog):
    c=configured('salesforce')
    c._session.headers=HeadersFailGet(c._session.headers)
    c._session.post=Mock(return_value=response(body={
        'access_token':'REVIEW_NEW_ACCESS_TOKEN_LONG_6c9a',
        'instance_url':'https://instance.invalid/'+LONG,
    }))
    assert c._secret_values() is _SECRET_COLLECTION_FAILED
    caplog.set_level(logging.INFO);caplog.clear()
    c.authenticate_with_code('synthetic-code','https://callback.invalid')
    assert LONG not in caplog.text

@pytest.mark.parametrize('secret',[LONG,SHORT])
def test_zoho_update_provider_error_is_configured_value_safe(secret):
    c=configured('zoho',secret)
    c._session.request=Mock(return_value=response(body={'data':[{
        'status':'error','code':'INVALID_DATA','message':'upstream refused '+secret,
    }]}))
    with pytest.raises(ConnectorError) as caught:c.update_record('Contacts','ordinary-id',{'Last_Name':'Example'})
    assert secret not in str(caught.value)
    assert secret not in repr(caught.value)

def test_salesforce_security_token_is_a_configured_credential():
    token='REVIEW_ONLY_SF_SECURITY_CREDENTIAL_f8a1'
    c=SalesforceConnector(client_id='ordinary-id',client_secret=LONG,
                          username='ordinary-user',password='REVIEW_PASSWORD_LONG_5efc',security_token=token)
    c._session.post=Mock(return_value=response(400,{'error_description':'upstream refused '+token}))
    with pytest.raises(ConnectorError) as caught:c.authenticate()
    assert c._session.post.call_args.kwargs['data']['password']=='REVIEW_PASSWORD_LONG_5efc'+token
    assert token not in str(caught.value)

@pytest.mark.parametrize('provider',['salesforce','hubspot','zoho','dynamics'])
def test_cached_logger_tracks_ordinary_attribute_rotation(provider,caplog):
    c=configured(provider);cached=c._log
    c._client_secret=c._access_token=NEW;c._session.headers['Authorization']='Bearer '+NEW
    caplog.set_level(logging.INFO);caplog.clear()
    assert cached is c._log
    c._log.info('Synthetic upstream result: %s',NEW)
    assert NEW not in caplog.text

@pytest.mark.parametrize('provider',['salesforce','hubspot','zoho','dynamics'])
def test_cached_logger_tracks_changed_collector_policy(provider,caplog):
    c=configured(provider);_ = c._log
    c._secret_values=lambda:[NEW]
    caplog.set_level(logging.INFO);caplog.clear()
    c._log.info('Synthetic upstream result: %s',NEW)
    assert NEW not in caplog.text
