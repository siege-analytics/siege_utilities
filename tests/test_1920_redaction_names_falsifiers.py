"""Credential-context falsifiers for the #1920 item 3b narrowing.

These are the independent review's frozen cases, kept as permanent tests: a
quoted ``code`` or ``key`` field may keep an ordinary literal value, but a
credential nested inside such a value (userinfo URLs, encoded nested OAuth
codes, JSON-string payloads with credential or header names, repeated JSON
encoding, configured values of any length or escaping depth) must stay
redacted on every diagnostic surface. All secrets are synthetic.
"""
import json
import logging
from unittest.mock import Mock
from urllib.parse import quote

import pytest

from siege_utilities.connectors._protocol import ConnectorError, UpsertError, UpsertResult
from siege_utilities.core._http import redact_secrets
from tests.crm_connector_factories import connector, response

SECRET = 'synth_upstream_credential_1920c_XYZ'
KNOWN_ESCAPED_SECRET = 'synth"\\Ω /+KNOWN_1920C_SUFFIX'
CREDENTIALS = [
    'client_secret', 'refresh_token', 'access_token', 'token', 'password', 'assertion',
    'client_assertion', 'secret', 'private_key', 'api_key', 'apikey', 'api-key', 'x-api-key',
]


def credential_url(kind):
    if kind == 'userinfo':
        return 'https://reader:' + SECRET + '@api.example.test/private'
    return 'https://h.example.test/?next=' + quote('https://id.example.test/cb?code=' + SECRET, safe='')


def wrapped(field, text, style='json'):
    return json.dumps({field: text}) if style == 'json' else repr({field: text})


def shaped(shape):
    return credential_url(shape) if shape != 'json-credential-string' else json.dumps({'access_token': SECRET})


@pytest.mark.parametrize('field', ['code', 'key'])
@pytest.mark.parametrize('kind', ['userinfo', 'nested-encoded-code'])
@pytest.mark.parametrize('style', ['json', 'mapping'])
def test_credential_url_inside_preserved_field_remains_redacted(field, kind, style):
    text = wrapped(field, credential_url(kind), style)
    assert SECRET not in redact_secrets(text)


@pytest.mark.parametrize('field', ['code', 'key'])
@pytest.mark.parametrize('credential', CREDENTIALS)
def test_json_string_credential_payload_inside_preserved_field_remains_redacted(field, credential):
    text = wrapped(field, json.dumps({credential: SECRET}))
    assert SECRET not in redact_secrets(text)


@pytest.mark.parametrize('field', ['code', 'key'])
@pytest.mark.parametrize('header', ['Authorization', 'X-Api-Key'])
def test_json_string_header_payload_inside_preserved_field_remains_redacted(field, header):
    text = wrapped(field, json.dumps({header: SECRET}))
    assert SECRET not in redact_secrets(text)


def test_repeated_json_string_encoding_still_protects_credential():
    text = wrapped('key', json.dumps(json.dumps({'access_token': SECRET})))
    assert SECRET not in redact_secrets(text)


@pytest.mark.parametrize('field', ['code', 'key'])
@pytest.mark.parametrize('secret', ['xY7', 'x', 'xy+Ω'])
def test_configured_short_value_in_preserved_field_is_not_disclosed(field, secret):
    text = json.dumps({field: secret}, ensure_ascii=False)
    assert secret not in redact_secrets(text, values=(secret,))


@pytest.mark.parametrize('shape', ['userinfo', 'nested-encoded-code', 'json-credential-string'])
@pytest.mark.parametrize('surface', ['error-message', 'upsert-error-message', 'upsert-result-repr', 'logger'])
def test_unconfigured_upstream_credential_does_not_escape_normal_diagnostic_objects(shape, surface, caplog):
    text = wrapped('key', shaped(shape))
    if surface == 'error-message':
        observed = str(ConnectorError(text))
    elif surface == 'upsert-error-message':
        observed = UpsertError(0, text).message
    elif surface == 'upsert-result-repr':
        observed = repr(UpsertResult(0, 1, errors=[UpsertError(0, text)]))
    else:
        c = connector('dynamics')
        caplog.set_level(logging.WARNING)
        c._log.warning('%s', text)
        observed = caplog.text
    assert SECRET not in observed


@pytest.mark.parametrize('shape', ['userinfo', 'nested-encoded-code', 'json-credential-string'])
def test_native_dynamics_http_error_does_not_expose_unknown_upstream_credentials(shape, caplog):
    c = connector('dynamics')
    text = wrapped('key', shaped(shape))
    c._session.request = Mock(return_value=response(400, {'error': {'message': text}}))
    with pytest.raises(ConnectorError) as caught:
        c.request('POST', '/api/data/v9.2/accounts', json_body={'name': 'ordinary'})
    assert SECRET not in str(caught.value) + repr(caught.value) + caplog.text


# Bare (unwrapped) forms are the pre-existing gaps tracked by #1987; this pins
# that PR C does not claim to fix them. Update it when #1987 lands.
@pytest.mark.parametrize('shape', ['userinfo', 'nested-encoded-code'])
def test_bare_disclosed_gaps_are_not_silently_claimed_fixed(shape):
    text = credential_url(shape)
    assert redact_secrets(text) == text


@pytest.mark.parametrize('field', ['code', 'key'])
@pytest.mark.parametrize('shape', ['userinfo', 'nested-encoded-code', 'json-credential-string'])
def test_known_long_value_is_still_redacted_inside_preserved_fields(field, shape):
    assert SECRET not in redact_secrets(wrapped(field, shaped(shape)), values=(SECRET,))


@pytest.mark.parametrize('field', ['code', 'key'])
@pytest.mark.parametrize('inner_field', ['code', 'access_token'])
@pytest.mark.parametrize('depth', [1, 2])
def test_nested_json_string_cannot_expose_configured_credential(field, inner_field, depth):
    payload = json.dumps({inner_field: KNOWN_ESCAPED_SECRET})
    for _ in range(depth - 1):
        payload = json.dumps(payload)
    result = redact_secrets(json.dumps({field: payload}), values=(KNOWN_ESCAPED_SECRET,))
    # The stable literal suffix survives every JSON escape layer, so it must not appear.
    assert 'KNOWN_1920C_SUFFIX' not in result


@pytest.mark.parametrize('surface', ['logger', 'public-http-error'])
def test_native_consumer_does_not_expose_nested_configured_value(surface, caplog):
    c = connector('dynamics')
    c._access_token = KNOWN_ESCAPED_SECRET
    text = json.dumps({'key': json.dumps({'access_token': KNOWN_ESCAPED_SECRET})})
    if surface == 'logger':
        caplog.set_level(logging.WARNING)
        c._log.warning('%s', text)
        observed = caplog.text
    else:
        c._session.request = Mock(return_value=response(400, {'error': {'message': text}}))
        with pytest.raises(ConnectorError) as caught:
            c.request('POST', '/api/data/v9.2/accounts', json_body={'name': 'ordinary'})
        observed = str(caught.value) + repr(caught.value)
    assert 'KNOWN_1920C_SUFFIX' not in observed
