"""Independent synthetic-credential controls for the R6 public boundary."""
import asyncio
import base64
import inspect
import logging
import traceback
from unittest.mock import Mock

import pytest

from siege_utilities.connectors._protocol import _SECRET_COLLECTION_FAILED, _SecretRedactionMixin as M
from tests.crm_connector_factories import connector

PROVIDERS = ['salesforce', 'hubspot', 'zoho', 'dynamics']
SHORT = 'Z7q9xA'
LONG = 'DUMMYCONFIGUREDSECRET7a4c'


def configured(provider, secret=SHORT):
    c = connector(provider)
    c._client_secret = c._access_token = secret
    c._refresh_token = None
    c._retry_attempts = 1
    c._session.headers['Authorization'] = 'Bearer ' + secret
    return c


def invoke(c, error):
    c._session.request = Mock(side_effect=error)
    with pytest.raises(Exception) as info:
        c.request('GET', '/ordinary')
    assert c._session.request.call_count == 1
    return info.value


def safe_surfaces(error, secret):
    shown = '\n'.join([str(error), repr(error), repr(error.args), ''.join(traceback.format_exception(error))])
    assert secret not in shown, shown


@pytest.mark.parametrize('provider', PROVIDERS)
@pytest.mark.parametrize('mode', ['short', 'failed'])
@pytest.mark.parametrize('encoding', ['raw', 'base64', 'unicode-escape'])
def test_strict_log_cannot_trust_rendered_template_with_args(provider, mode, encoding, caplog):
    secret = SHORT if mode == 'short' else LONG
    c = configured(provider, secret)
    if mode == 'failed':
        c._secret_values = lambda: _SECRET_COLLECTION_FAILED
    payload = secret if encoding == 'raw' else base64.b64encode(secret.encode()).decode() if encoding == 'base64' else ''.join('\\u%04x' % ord(ch) for ch in secret)
    caplog.set_level(logging.ERROR)
    caplog.clear()
    # Presence of an ordinary %-argument does not make this caller-rendered text trusted.
    c._log.error('upstream ' + payload + ' %s', 'ordinary')
    messages = '\n'.join(r.getMessage() for r in caplog.records)
    assert payload not in messages, messages


class ForgedInt(int):
    def __format__(self, spec):
        return SHORT

    def __str__(self):
        return SHORT


@pytest.mark.parametrize('provider', PROVIDERS)
@pytest.mark.parametrize('attribute', ['status_code', 'status'])
def test_numeric_status_does_not_invoke_subclass_rendering(provider, attribute):
    error = ValueError(SHORT)
    setattr(error, attribute, ForgedInt(429))
    safe_surfaces(invoke(configured(provider), error), SHORT)


@pytest.mark.parametrize('provider', PROVIDERS)
@pytest.mark.parametrize('attribute', ['status_code', 'status', 'retry_after'])
def test_metadata_getter_fault_cannot_escape_sanitization(provider, attribute):
    def fail(self):
        raise ValueError(SHORT)
    cls = type('GetterError', (Exception,), {attribute: property(fail)})
    error = cls(SHORT)
    safe_surfaces(invoke(configured(provider), error), SHORT)


@pytest.mark.parametrize('provider', PROVIDERS)
@pytest.mark.parametrize('attribute', ['status_code', 'status', 'retry_after'])
@pytest.mark.parametrize('secret', [SHORT, LONG])
def test_rich_error_metadata_is_not_copied_back_raw(provider, attribute, secret):
    def init(self, message):
        Exception.__init__(self, message)
        setattr(self, attribute, message)
    def render(self):
        return str(getattr(self, attribute))
    cls = type('RichMetadataError', (Exception,), {'__init__': init, '__str__': render})
    safe_surfaces(invoke(configured(provider, secret), cls(secret)), secret)


@pytest.mark.parametrize('provider', PROVIDERS)
@pytest.mark.parametrize('status', [None, False, 0, 99, 100, 429, 599, 600, -1, '429', SHORT])
def test_validated_status_message_controls(provider, status):
    error = ValueError(SHORT)
    error.status_code = status
    result = invoke(configured(provider), error)
    expected = 'ValueError (HTTP %s)' % status if type(status) is int and 100 <= status <= 599 else 'ValueError'
    assert str(result) == expected
    safe_surfaces(result, SHORT)


def prepare(cls, secret):
    c = cls()
    c._client_secret = secret
    return c


@pytest.mark.parametrize('shape', ['sync', 'async', 'generator', 'async-generator', 'property-get', 'property-set', 'property-del', 'init-after', 'classmethod', 'staticmethod'])
@pytest.mark.parametrize('secret', [SHORT, LONG])
def test_promised_callable_shapes_preserve_failure_and_privacy(shape, secret):
    def fail(self):
        raise ValueError(secret)
    if shape == 'sync':
        class C(M):
            go = fail
        run = prepare(C, secret).go
    elif shape == 'async':
        class C(M):
            async def go(self):
                raise ValueError(secret)
        run = lambda: asyncio.run(prepare(C, secret).go())
    elif shape == 'generator':
        class C(M):
            def go(self):
                yield 'ordinary'
                raise ValueError(secret)
        run = lambda: list(prepare(C, secret).go())
    elif shape == 'async-generator':
        class C(M):
            async def go(self):
                yield 'ordinary'
                raise ValueError(secret)
        async def consume():
            return [item async for item in prepare(C, secret).go()]
        run = lambda: asyncio.run(consume())
    elif shape.startswith('property'):
        class C(M):
            @property
            def go(self):
                raise ValueError(secret)
            @go.setter
            def go(self, value):
                raise ValueError(secret)
            @go.deleter
            def go(self):
                raise ValueError(secret)
        c = prepare(C, secret)
        run = (lambda: c.go) if shape == 'property-get' else (lambda: setattr(c, 'go', 'ordinary')) if shape == 'property-set' else (lambda: delattr(c, 'go'))
    elif shape == 'init-after':
        class C(M):
            def __init__(self):
                self._client_secret = secret
                raise ValueError(secret)
        run = C
    elif shape == 'classmethod':
        class C(M):
            _client_secret = secret
            @classmethod
            def go(cls):
                raise ValueError(secret)
        run = C.go
    else:
        class C(M):
            _client_secret = secret
            @staticmethod
            def go(value):
                raise ValueError(secret)
        run = lambda: C.go(secret)
    with pytest.raises(Exception) as info:
        run()
    assert isinstance(info.value, ValueError), type(info.value).__name__
    safe_surfaces(info.value, secret)


def test_async_generator_send_protocol_preserved():
    class C(M):
        async def go(self):
            received = yield 'ready'
            yield received
    async def check():
        g = prepare(C, LONG).go()
        assert await g.__anext__() == 'ready'
        assert await g.asend(37) == 37
        await g.aclose()
    asyncio.run(check())


def test_async_generator_throw_protocol_preserved():
    class C(M):
        async def go(self):
            try:
                yield 'ready'
            except KeyError:
                yield 'handled'
    async def check():
        g = prepare(C, LONG).go()
        assert await g.__anext__() == 'ready'
        assert await g.athrow(KeyError('ordinary')) == 'handled'
        await g.aclose()
    asyncio.run(check())


def test_async_generator_close_protocol_preserved():
    closed = []
    class C(M):
        async def go(self):
            try:
                yield 'ready'
            finally:
                closed.append(True)
    async def check():
        g = prepare(C, LONG).go()
        assert await g.__anext__() == 'ready'
        await g.aclose()
        assert closed == [True]
    asyncio.run(check())


def test_async_generator_introspection_control():
    class C(M):
        async def go(self):
            yield 'ordinary'
    assert inspect.isasyncgenfunction(C.go)
