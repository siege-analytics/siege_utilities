"""CRM connectors never expose configured credentials or upstream detail.

Covers short credentials (one and seven characters, where value redaction is
unsafe, so all upstream detail is suppressed), success logs, UpsertResult
rendering and copying, error code/field context, token-exchange failures,
secret-collection failures, and percent-encoded path echoes, across Salesforce,
HubSpot, Zoho and Dynamics. All credentials are synthetic; every HTTP send is
intercepted.
"""
import logging
import re
import traceback
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from urllib.parse import quote
import pandas as pd
import pytest
import requests
from siege_utilities.connectors._protocol import ConnectorError, _SECRET_COLLECTION_FAILED
from siege_utilities.core._http import redact_secrets
from tests.crm_connector_factories import connector, response, batch_response

PROVIDERS=['salesforce','hubspot','zoho','dynamics']
SECRET='R4_REVIEW_SYNTHETIC_ONLY_c18af7'
DETAIL='UPSTREAM_R4_DETAIL_ae71'

@pytest.fixture(autouse=True)
def no_network_or_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(requests.Session,'send',Mock(side_effect=AssertionError('NETWORK FORBIDDEN')))
    monkeypatch.setattr('time.sleep',Mock())

def configured(provider: str, secret: str = SECRET) -> Any:
    c=connector(provider);c._client_secret=c._access_token=secret
    c._session.headers['Authorization']='Bearer '+secret;c._refresh_token=None;c._retry_attempts=1
    return c

def error_body(provider: str, text: str) -> Any:
    return [{'message':text}] if provider=='salesforce' else {'error':{'message':text}} if provider=='dynamics' else {'message':text}

def public_upsert(c: Any, provider: str, error: dict[str, Any] | None = None, success: bool = False) -> Any:
    if provider=='dynamics':
        c._session.post=Mock(return_value=batch_response([(1,201 if success else 400,{} if success else {'error':error})]))
    else:
        b=({'salesforce':[{'success':True,'id':SECRET,'created':True}], 'hubspot':{'results':[{'id':SECRET,'new':True}]}, 'zoho':{'data':[{'status':'success','action':'insert','details':{'id':SECRET}}]}} if success else
           {'salesforce':[{'success':False,'errors':[error]}], 'hubspot':{'results':[],'errors':[error]}, 'zoho':{'data':[{'status':'error',**error}]}})[provider]
        c._session.request=Mock(return_value=response(body=b))
    return c.upsert_records('contacts',pd.DataFrame([{'key':SECRET if success else 'business-key'}]),'key')

def displays(exc: BaseException) -> str:
    text=str(exc)+'\n'+repr(exc)+'\n'+''.join(traceback.format_exception(type(exc),exc,exc.__traceback__))
    seen=set();todo=[exc]
    while todo:
        e=todo.pop()
        if e is None or id(e) in seen:continue
        seen.add(id(e));text+='\n'+str(e)+'\n'+repr(e);todo += [e.__cause__,e.__context__]
    return text

@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('secret',['E','Z7q!9xA'])
@pytest.mark.parametrize('status',[403,422])
def test_short_credentials_suppress_all_general_response_detail(provider: str, secret: str, status: int) -> None:
    c=configured(provider,secret);c._session.request=Mock(return_value=response(status,error_body(provider,DETAIL+' '+secret)))
    with pytest.raises(ConnectorError) as caught:c.request('POST','/records')
    assert DETAIL not in displays(caught.value)

@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('secret',['E','Z7q!9xA'])
def test_short_credentials_suppress_upsert_diagnostic_fields(provider: str, secret: str) -> None:
    c=configured(provider,secret)
    r=public_upsert(c,provider,{'message':DETAIL+' '+secret,'code':DETAIL,'statusCode':DETAIL,'category':DETAIL,'fields':[DETAIL]})
    assert r.failure_count==1
    assert DETAIL not in repr(r)

@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('secret',['E','Z7q!9xA'])
def test_short_credentials_suppress_request_derived_log_detail(
    provider: str, secret: str, caplog: pytest.LogCaptureFixture,
) -> None:
    c=configured(provider,secret);c._session.request=Mock(return_value=response(503))
    caplog.set_level(logging.WARNING)
    with pytest.raises(ConnectorError):c.request('POST','/records/'+DETAIL+'_'+secret)
    assert caplog.records
    assert DETAIL not in caplog.text

@pytest.mark.parametrize('provider',PROVIDERS)
def test_success_record_log_does_not_echo_configured_credential(
    provider: str, caplog: pytest.LogCaptureFixture,
) -> None:
    c=configured(provider)
    b={'salesforce':{'id':SECRET,'success':True},'hubspot':{'id':SECRET},'zoho':{'data':[{'status':'success','details':{'id':SECRET}}]},'dynamics':{'contactid':SECRET}}[provider]
    c._session.request=Mock(return_value=response(201,b));caplog.set_level(logging.INFO)
    returned=c.create_record('contacts',{'key':'business-key','api_key':'business-value'})
    assert returned==SECRET  # returned business data MUST NOT be changed
    assert caplog.records
    assert SECRET not in caplog.text
    assert all(SECRET not in r.getMessage() and SECRET not in repr(r.msg) and SECRET not in repr(r.args) for r in caplog.records)

@pytest.mark.parametrize('provider',PROVIDERS)
def test_upsert_id_data_preserved_but_rendered_copy_redacted(provider: str) -> None:
    c=configured(provider);r=public_upsert(c,provider,success=True)
    assert r.ok and r.created_ids+r.updated_ids==[SECRET]
    assert SECRET not in repr(r)

@pytest.mark.parametrize('provider',PROVIDERS)
def test_error_code_has_configured_value_context(provider: str) -> None:
    c=configured(provider)
    r=public_upsert(c,provider,{'message':'ordinary failure','code':SECRET,'statusCode':SECRET,'category':SECRET})
    assert r.failure_count==1 and r.errors[0].code=='[REDACTED]'
    assert SECRET not in repr(r)

def test_salesforce_error_field_has_configured_value_context() -> None:
    c=configured('salesforce')
    r=public_upsert(c,'salesforce',{'message':'ordinary failure','statusCode':'bad','fields':[SECRET]})
    assert r.errors[0].field=='[REDACTED]' and SECRET not in repr(r)

def test_salesforce_bulk_error_message_and_code_have_value_context() -> None:
    c=configured('salesforce');r=response();r._content=('sf__Error\n'+SECRET+'\n').encode();c._session.get=Mock(return_value=r)
    result=c._bulk_collect_results('job-r4',{'state':'JobComplete','numberRecordsProcessed':1,'numberRecordsFailed':1})
    assert result.failure_count==1
    assert result.errors[0].message=='[REDACTED]' and result.errors[0].code=='[REDACTED]'
    assert SECRET not in repr(result)

@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('secret',['E','Z7q!9xA'])
def test_short_marker_collision_auth_drops_upstream_content_not_characters(provider: str, secret: str) -> None:
    c=configured(provider,secret);b={'error':DETAIL+' '+secret,'error_description':DETAIL+' '+secret,'message':DETAIL+' '+secret}
    if provider=='dynamics':
        c._scope=['scope'];c._msal_app=SimpleNamespace(acquire_token_for_client=Mock(return_value=b));invoke=c._auth_client_credentials
    else:
        c._session.post=Mock(return_value=response(400,b));invoke=lambda:c._exchange_token('https://auth.example.test/token',{'client_secret':secret})
    with pytest.raises(ConnectorError) as caught:invoke()
    assert DETAIL not in displays(caught.value)  # asserts upstream content is gone, not secret-char absence

@pytest.mark.parametrize('provider',PROVIDERS)
def test_collector_failure_signal_and_hidden_chains_are_safe(provider: str) -> None:
    c=configured(provider)
    class BrokenHeaders(dict):
        def get(self,key,default=None):raise ValueError('token='+SECRET)
    c._session.headers=BrokenHeaders()
    assert c._secret_values() is _SECRET_COLLECTION_FAILED
    c._session.request=Mock(return_value=response(403,error_body(provider,DETAIL+' '+SECRET)))
    with pytest.raises(ConnectorError) as caught:c.request('POST','/records')
    assert SECRET not in displays(caught.value) and DETAIL not in displays(caught.value)
    assert caught.value.__cause__ is None and caught.value.__context__ is None

@pytest.mark.parametrize('provider',PROVIDERS)
@pytest.mark.parametrize('kind',[KeyboardInterrupt,SystemExit])
def test_collection_does_not_swallow_baseexceptions(provider: str, kind: type[BaseException]) -> None:
    c=configured(provider)
    class InterruptedHeaders(dict):
        def get(self,key,default=None):raise kind('requested stop')
    c._session.headers=InterruptedHeaders()
    with pytest.raises(kind):c._secret_values()

def test_whole_value_replacement_does_not_rescan_inserted_markers() -> None:
    assert redact_secrets(SECRET,values=[SECRET,'REDACTED'])=='[REDACTED]'

@pytest.mark.parametrize('provider',PROVIDERS)
def test_valid_lowercase_percent_hex_path_encoding_is_redacted(provider: str) -> None:
    secret='R4_SYNTHETIC_ONLY /+"\\Ω_end9f2a';c=configured(provider,secret)
    encoded=re.sub(r'%[0-9A-F]{2}',lambda m:m[0].lower(),quote(secret,safe=''))
    c._session.request=Mock(return_value=response(404))
    with pytest.raises(ConnectorError) as caught:c.request('POST','/records/'+encoded)
    assert encoded not in displays(caught.value)

@pytest.mark.parametrize('provider',['salesforce','zoho'])
def test_application_level_create_failure_redacts_provider_message(provider: str) -> None:
    c=configured(provider)
    b={'success':False,'errors':[{'message':SECRET}]} if provider=='salesforce' else {'data':[{'status':'error','message':SECRET}]}
    c._session.request=Mock(return_value=response(200,b))
    with pytest.raises(ConnectorError) as caught:c.create_record('contacts',{'key':'business-key'})
    assert SECRET not in displays(caught.value)


def test_upsert_result_copies_do_not_copy_the_bound_connector() -> None:
    """asdict and deepcopy copy result data, never the connector behind ``redact``."""
    import copy
    import dataclasses

    c=configured('dynamics')
    r=public_upsert(c,'dynamics',success=True)
    assert 'redact' not in [f.name for f in dataclasses.fields(r)]
    assert set(dataclasses.asdict(r)) == {'success_count','failure_count','created_ids','updated_ids','errors'}
    clone=copy.deepcopy(r)
    assert clone._redact.__self__ is c  # the redactor is shared, not deep-copied
    assert clone.created_ids == r.created_ids and clone.created_ids is not r.created_ids
    assert SECRET not in repr(clone)
    assert clone == r
