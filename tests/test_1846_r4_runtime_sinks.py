import logging,traceback
from unittest.mock import Mock
import pandas as pd
import pytest,requests
from siege_utilities.connectors._protocol import ConnectorError,_SECRET_COLLECTION_FAILED
from tests.test_1417_crm_retry_idempotency import connector,response
PROVIDERS=['salesforce','hubspot','zoho','dynamics']
LONG='DUMMYCONFIGUREDSECRET7a4c';SHORT='Z7q9xA'
@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(requests.Session,'send',Mock(side_effect=AssertionError('NO NETWORK')))
    monkeypatch.setattr('time.sleep',Mock())
def configured(provider,secret):
    c=connector(provider);c._client_secret=c._access_token=secret;c._refresh_token=None;c._retry_attempts=1
    c._session.headers['Authorization']='Bearer '+secret
    return c
@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('secret',[LONG,SHORT])
def test_update_success_type_logging(provider,secret,caplog):
    c=configured(provider,secret);c._session.request=Mock(return_value=response(body={'data':[{'status':'success'}]}))
    caplog.set_level(logging.INFO);caplog.clear()
    assert c.update_record(secret,'ordinary-id',{'name':'Synthetic'}) is True
    assert secret in c._session.request.call_args.args[1]
    assert secret not in caplog.text
@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('secret',[LONG,SHORT])
def test_empty_upsert_type_logging(provider,secret,caplog):
    c=configured(provider,secret);c._session.request=Mock(side_effect=AssertionError('No HTTP expected'))
    caplog.set_level(logging.INFO);caplog.clear()
    assert c.upsert_records(secret,pd.DataFrame(),'external_id').total==0
    c._session.request.assert_not_called()
    assert secret not in caplog.text
@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('secret',[LONG,SHORT])
@pytest.mark.parametrize('kind',['sentinel','invalid-key'])
def test_public_upsert_helper_error_value_redaction(provider,secret,kind):
    c=configured(provider,secret);c._session.request=Mock(side_effect=AssertionError('No HTTP expected'))
    nested={secret:pd.NA} if kind=='sentinel' else {('prefix',secret):'ordinary'}
    frame=pd.DataFrame({'external_id':['ordinary'],'nested':[nested]})
    with pytest.raises(ConnectorError) as caught:c.upsert_records('Contact',frame,'external_id')
    c._session.request.assert_not_called()
    surfaces=[str(caught.value),repr(caught.value),repr(caught.value.args),''.join(traceback.format_exception(caught.value))]
    assert all(secret not in s for s in surfaces)
@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('secret',[LONG,SHORT])
def test_request_custom_method_diagnostic_redaction(provider,secret):
    c=configured(provider,secret);c._session.request=Mock(return_value=response(429,headers={'Retry-After':'0'}))
    with pytest.raises(ConnectorError) as caught:c.request(secret,'/ordinary')
    assert c._session.request.call_args.args[0]==secret
    assert secret not in str(caught.value)
@pytest.mark.parametrize('secret',[LONG,SHORT])
def test_zoho_update_error_type_fixed(secret):
    c=configured('zoho',secret);c._session.request=Mock(return_value=response(body={'data':[{'status':'error','message':'ordinary'}]}))
    with pytest.raises(ConnectorError) as caught:c.update_record(secret,'ordinary-id',{'name':'Synthetic'})
    assert secret not in str(caught.value)
def bulk_failed(secret):
    c=configured('salesforce',secret)
    c._session.request=Mock(side_effect=[response(body={'id':'ordinary-job'}),response(body={'state':'UploadComplete'}),response(body={'state':secret})])
    c._session.put=Mock(return_value=response(201))
    return c
@pytest.mark.parametrize('state',['Failed','Aborted'])
def test_bulk_terminal_state_exception_fixed(state):
    c=bulk_failed(state)
    with pytest.raises(ConnectorError) as caught:c.bulk_insert('Contact',pd.DataFrame({'LastName':['Synthetic']}))
    assert state not in str(caught.value)
@pytest.mark.parametrize('state',['Failed','Aborted'])
def test_bulk_poll_state_log_short_overlap(state,caplog):
    c=bulk_failed(state);caplog.set_level(logging.INFO);caplog.clear()
    with pytest.raises(ConnectorError):c.bulk_insert('Contact',pd.DataFrame({'LastName':['Synthetic']}))
    assert state not in caplog.text
@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('failure',[False,True])
@pytest.mark.parametrize('channel',['extra','exc_info'])
def test_logger_context_diagnostic_redaction(provider,failure,channel,caplog):
    c=configured(provider,LONG)
    if failure:c._secret_values=lambda:_SECRET_COLLECTION_FAILED
    caplog.set_level(logging.INFO);caplog.clear()
    if channel=='extra':
        c._log.error('Trusted static template',extra={'diagnostic':LONG})
        # extra is dropped entirely (#1846 R-1846-6): no record carries the
        # diagnostic field, so nothing can render it.
        assert all(not hasattr(r,'diagnostic') for r in caplog.records)
        shown='\n'.join(r.getMessage() for r in caplog.records)
    else:
        try:raise ValueError(LONG)
        except ValueError:c._log.error('Trusted static template',exc_info=True)
        shown=caplog.text
    assert LONG not in shown
