"""CRM connectors hide API keys and configured client secrets.

An ``X-Api-Key`` header value echoed in a JSON or form-encoded error body, a
client secret echoed by a token endpoint, and an ``api_key=`` value in an
upsert error must all stay out of the raised error and the UpsertResult repr.
Synthetic values; every send is intercepted.
"""
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pandas as pd
import pytest
from siege_utilities.connectors._protocol import ConnectorError
from tests.crm_connector_factories import connector, response, batch_response

SENTINEL = 'REVIEW_SYNTHETIC_ONLY_c2f7a6'
PROVIDERS = ['salesforce', 'hubspot', 'zoho', 'dynamics']

@pytest.mark.parametrize('provider', PROVIDERS)
@pytest.mark.parametrize('surface', ['api_key_json', 'api_key_form'])
def test_api_key_diagnostics_absent(provider: str, surface: str) -> None:
    c = connector(provider)
    c._client_secret = None
    c._username = c._password = None
    c._session.headers['X-Api-Key'] = SENTINEL
    text = json.dumps({'api_key': SENTINEL}) if surface.endswith('json') else 'api_key='+SENTINEL+'&normal=visible'
    body = [{'message': text}] if provider == 'salesforce' else {'error': {'message': text}} if provider == 'dynamics' else {'message': text}
    c._session.request = Mock(return_value=response(401, body))
    with pytest.raises(ConnectorError) as caught:
        c.request('POST', '/records', json_body={'api_key': SENTINEL})
    assert SENTINEL not in str(caught.value)

@pytest.mark.parametrize('provider', PROVIDERS)
def test_configured_client_secret_absent_after_extraction(provider: str) -> None:
    c = connector(provider)
    c._client_secret = SENTINEL
    body = {'error': SENTINEL, 'error_description': SENTINEL, 'message': SENTINEL}
    if provider == 'dynamics':
        c._scope = ['scope']
        c._msal_app = SimpleNamespace(acquire_token_for_client=Mock(return_value=body))
        invoke = c._auth_client_credentials
    else:
        c._session.post = Mock(return_value=response(400, body))
        invoke = lambda: c._exchange_token('https://auth.example.test/token', {'client_secret': SENTINEL})
    with pytest.raises(ConnectorError) as caught:
        invoke()
    assert SENTINEL not in str(caught.value)

@pytest.mark.parametrize('provider', PROVIDERS)
def test_public_upsert_result_api_key_absent(provider: str) -> None:
    c = connector(provider)
    error = {'message': 'api_key='+SENTINEL, 'code': 'bad', 'statusCode': 'bad', 'category': 'bad'}
    if provider == 'dynamics':
        c._session.post = Mock(return_value=batch_response([(1, 400, {'error': error})]))
    else:
        body = {'salesforce': [{'success': False, 'errors': [error]}],
                'hubspot': {'results': [], 'errors': [error]},
                'zoho': {'data': [{'status': 'error', **error}]}}[provider]
        c._session.request = Mock(return_value=response(body=body))
    result = c.upsert_records('contacts', pd.DataFrame({'key': ['a']}), 'key')
    assert not result.ok
    assert SENTINEL not in repr(result)
