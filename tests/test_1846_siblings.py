import logging
from unittest.mock import Mock
import pandas as pd
import pytest,requests
from siege_utilities.connectors._protocol import ConnectorError,_SECRET_COLLECTION_FAILED
from tests.crm_connector_factories import connector,response
LONG='DUMMYCONFIGUREDSECRET7a4c'
SHORT='Z7q9xA'
@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(requests.Session,'send',Mock(side_effect=AssertionError('NO NETWORK')))
    monkeypatch.setattr('time.sleep',Mock())
def configured(provider,s):
    c=connector(provider);c._client_secret=c._access_token=s;c._refresh_token=None
    c._session.headers['Authorization']='Bearer '+s;c._retry_attempts=1
    return c
@pytest.mark.parametrize('provider',['salesforce','hubspot','zoho','dynamics'])
@pytest.mark.parametrize('secret',[LONG,SHORT])
def test_create_error_object_type_is_not_trusted(provider,secret):
    c=configured(provider,secret)
    body={'success':False,'errors':[{'message':'ordinary failure'}]} if provider=='salesforce' else {'data':[{'status':'error','message':'ordinary failure'}]} if provider=='zoho' else {}
    c._session.request=Mock(return_value=response(body=body))
    with pytest.raises(ConnectorError) as e:c.create_record(secret,{'name':'Synthetic'})
    assert secret not in str(e.value)
@pytest.mark.parametrize('provider',['salesforce','hubspot','zoho','dynamics'])
def test_success_log_object_type_short_overlap(provider,caplog):
    c=configured(provider,SHORT)
    body={'success':True,'id':'ordinary-id'} if provider=='salesforce' else {'data':[{'status':'success','details':{'id':'ordinary-id'}}]} if provider=='zoho' else {'id':'ordinary-id'} if provider=='hubspot' else {SHORT+'id':'ordinary-id'}
    c._session.request=Mock(return_value=response(body=body))
    caplog.set_level(logging.INFO);caplog.clear()
    assert c.create_record(SHORT,{'name':'Synthetic'})=='ordinary-id'
    assert SHORT not in caplog.text
@pytest.mark.parametrize('secret',[LONG,SHORT])
def test_salesforce_public_bulk_timeout_upstream_id_is_redacted(secret,monkeypatch):
    c=configured('salesforce',secret)
    c._session.request=Mock(return_value=response(body={'id':secret}))
    c._session.put=Mock(return_value=response(201))
    monkeypatch.setattr('siege_utilities.connectors.salesforce.BULK_TIMEOUT',-1)
    with pytest.raises(ConnectorError) as e:c.bulk_insert('Contact',pd.DataFrame({'LastName':['Synthetic']}))
    assert c._session.put.call_args.args[0].endswith('/'+secret+'/batches')
    assert secret not in str(e.value)
@pytest.mark.parametrize('provider',['salesforce','hubspot','zoho','dynamics'])
@pytest.mark.parametrize('mode',['sentinel','nonsequence','raise'])
def test_logger_collector_failure_drops_all_arguments(provider,mode,caplog):
    c=configured(provider,LONG)
    def collect():
        if mode=='raise':raise ValueError(LONG)
        return _SECRET_COLLECTION_FAILED if mode=='sentinel' else 'unusable'
    c._secret_values=collect
    caplog.set_level(logging.INFO);caplog.clear()
    c._log.info('Trusted static template %s',LONG)
    assert LONG not in caplog.text and 'suppressed' in caplog.text
@pytest.mark.parametrize('provider',['salesforce','hubspot','zoho','dynamics'])
def test_public_client_id_is_not_treated_as_secret(provider):
    c=configured(provider,LONG);c._client_id='public-id'
    assert 'public-id' not in c._secret_values()
    assert c._redact_field('public-id')=='public-id'
