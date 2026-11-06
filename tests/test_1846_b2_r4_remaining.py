"""Round-4 B2 no-leak contract regressions for #1846 (#1460).

Adopted verbatim from the lively-thunder r3 review fixture
(sessions/261019-lively-thunder/data/r3/test_b2_remaining.py); imports already
resolve against the repo, so no bootstrap shim is needed. 96 assertions:
red at a9f772d8, green after the D1-D5 fix.
"""
import json
import logging
import traceback
from unittest.mock import Mock
from urllib.parse import quote, quote_plus
import pandas as pd
import pytest
from siege_utilities.connectors._protocol import ConnectorError
from tests.test_1417_crm_retry_idempotency import connector, response, batch_response

PROVIDERS=['salesforce','hubspot','zoho','dynamics']
SECRET='R3_SYNTHETIC_ONLY /+"\\Ω_end9f2a'
FORMS=[SECRET,quote(SECRET,safe=''),quote_plus(SECRET),json.dumps(SECRET)[1:-1]]

def configured(provider,secret=SECRET):
    c=connector(provider)
    c._client_secret=c._access_token=secret
    c._session.headers['Authorization']='Bearer '+secret
    c._refresh_token=None
    c._retry_attempts=1
    return c

def shown(exc):
    return str(exc)+'\n'+repr(exc)+'\n'+''.join(traceback.format_exception(type(exc),exc,exc.__traceback__))

@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('echo',FORMS)
def test_configured_echo_absent_from_public_upsert_result(provider,echo):
    c=configured(provider)
    e={'message':'Rejected credential '+echo,'code':'bad','statusCode':'bad','category':'bad'}
    if provider=='dynamics':c._session.post=Mock(return_value=batch_response([(1,400,{'error':e})]))
    else:
        b={'salesforce':[{'success':False,'errors':[e]}],'hubspot':{'results':[],'errors':[e]},'zoho':{'data':[{'status':'error',**e}]}}[provider]
        c._session.request=Mock(return_value=response(body=b))
    result=c.upsert_records('contacts',pd.DataFrame([{'key':'business-key'}]),'key')
    assert not result.ok
    assert echo not in '\n'.join(e.message for e in result.errors)
    assert echo not in repr(result)

@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('echo',FORMS)
@pytest.mark.parametrize('status',[404,429,503])
def test_configured_echo_absent_from_path_errors_and_logs(provider,echo,status,caplog):
    c=configured(provider)
    c._session.request=Mock(return_value=response(status,headers={'Retry-After':'0'}))
    caplog.set_level(logging.WARNING)
    with pytest.raises(ConnectorError) as caught:c.request('POST','/records/'+echo)
    assert echo not in shown(caught.value)
    assert echo not in caplog.text
    assert all(echo not in r.getMessage() and echo not in repr(r.msg) for r in caplog.records)

@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('secret',['Z7q!9xA','Z8q!9xAB'])
def test_seven_and_eight_character_credentials_are_both_secret(provider,secret):
    c=configured(provider,secret)
    b={'error':secret,'error_description':secret,'message':secret}
    if provider=='dynamics':
        c._scope=['scope'];c._msal_app=Mock();c._msal_app.acquire_token_for_client.return_value=b
        invoke=c._auth_client_credentials
    else:
        c._session.post=Mock(return_value=response(400,b))
        invoke=lambda:c._exchange_token('https://auth.example.test/token',{'client_secret':secret})
    with pytest.raises(ConnectorError) as caught:invoke()
    assert secret not in shown(caught.value)

@pytest.mark.parametrize('provider',PROVIDERS)
def test_header_lookup_valueerror_cannot_replace_safe_typed_diagnostic(provider):
    c=configured(provider)
    class BrokenHeaders(dict):
        def get(self,key,default=None):raise ValueError('header lookup failed: '+SECRET)
    c._session.headers=BrokenHeaders()
    b=[{'message':'ordinary failure'}] if provider=='salesforce' else {'error':{'message':'ordinary failure'}} if provider=='dynamics' else {'message':'ordinary failure'}
    c._session.request=Mock(return_value=response(403,b))
    with pytest.raises(ConnectorError) as caught:c.request('POST','/records')
    assert SECRET not in shown(caught.value)

@pytest.mark.parametrize('provider',PROVIDERS)
def test_long_credential_redacted_before_fallback_body_truncation(provider):
    secret='R3_LONG_SYNTHETIC_ONLY_'+('x9Q'*100)
    c=configured(provider,secret)
    r=response(403);r._content=('Rejected credential '+secret).encode()
    c._session.request=Mock(return_value=r)
    with pytest.raises(ConnectorError) as caught:c.request('POST','/records')
    assert secret[:64] not in shown(caught.value)

@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('echo',[SECRET,json.dumps(SECRET)[1:-1]])
@pytest.mark.parametrize('surface',['url','form'])
def test_configured_secret_suffix_not_exposed_after_syntax_redaction(provider,echo,surface):
    c=configured(provider)
    text=('https://upstream.example.test/?api_key=' if surface=='url' else 'api_key=')+echo
    b=[{'message':text}] if provider=='salesforce' else {'error':{'message':text}} if provider=='dynamics' else {'message':text}
    c._session.request=Mock(return_value=response(403,b))
    with pytest.raises(ConnectorError) as caught:c.request('POST','/records')
    # Known-value context must hide the full configured value, not merely its
    # prefix up to a space/quote, leaving the unique suffix exposed.
    assert '_end9f2a' not in shown(caught.value)
