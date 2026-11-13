"""Credentials supplied per call stay out of CRM diagnostics for the whole call.

A per-call Dynamics ``Authorization``/``X-Api-Key`` header and an OAuth
authorization code are sent by real public calls, so an upstream echo of them
must be value-redacted (or replaced by the trusted constant when the value is
short or could not be collected) in exception text and log records. That
covers the first response, the retry/replay, the nested token refresh and the
public error boundary. The echoes below carry no key or ``Bearer`` syntax, so
only value redaction can remove them. Request bytes stay exactly as supplied,
and the values are forgotten when the public call ends.

Offline: stub transports only; no live auth and no MSAL install (the Dynamics
refresh uses a per-instance ``_msal_app`` stub, as the existing suites do).
"""
from __future__ import annotations

import logging
import traceback
from collections.abc import Iterator, Mapping
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from urllib.parse import quote, quote_plus

import pytest

from siege_utilities.connectors._protocol import ConnectorAuthError, ConnectorError
from tests.crm_connector_factories import connector, response

PER_CALL = "dummy-per-call-credential-1846"
CODE = "dummy-oauth-authorization-code-1846"
SHORT = "dummy7c"
CALLBACK = "https://app.example.test/oauth/callback"


def shown(exc: BaseException) -> str:
    return "\n".join([
        str(exc), repr(exc),
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    ])


def logged(caplog: pytest.LogCaptureFixture) -> str:
    return caplog.text + "\n".join(record.getMessage() for record in caplog.records)


def dynamics(attempts: int = 1) -> Any:
    c = connector("dynamics")
    c._retry_attempts = attempts
    return c


def echo_body(value: str) -> dict:
    # Anonymous echo: no header name, no "Bearer", no key=value syntax.
    return {"error": {"message": f"credential {value} was rejected for this tenant"}}


CREDENTIAL_HEADERS = [
    ("Authorization", f"Bearer {PER_CALL}"),
    ("authorization", f"bearer {PER_CALL}"),
    ("Proxy-Authorization", f"Basic {PER_CALL}"),
    ("X-Api-Key", PER_CALL),
]


# -- Dynamics per-call headers: adversarial anonymous-echo controls ----------


@pytest.mark.parametrize("name,value", CREDENTIAL_HEADERS)
@pytest.mark.parametrize("status,error", [
    (400, ConnectorError), (401, ConnectorAuthError), (403, ConnectorAuthError),
])
def test_per_call_header_echo_is_redacted_and_ordinary_detail_kept(
    name: str, value: str, status: int, error: type,
) -> None:
    c = dynamics()
    c._session.request = Mock(return_value=response(status, echo_body(PER_CALL)))
    headers = {name: value, "Prefer": "return=representation"}

    with pytest.raises(error) as caught:
        c.request("POST", "/api/data/v9.2/contacts", json_body={"a": 1}, headers=headers)

    assert PER_CALL not in shown(caught.value)
    # Ordinary upstream detail is still reported.
    assert "was rejected for this tenant" in str(caught.value)
    # The request bytes are exactly what the caller supplied.
    sent = c._session.request.call_args.kwargs
    assert sent["headers"] == {name: value, "Prefer": "return=representation"}
    assert sent["json"] == {"a": 1}


def test_per_call_header_echo_is_redacted_at_the_public_error_boundary() -> None:
    c = dynamics()
    c._session.request = Mock(side_effect=RuntimeError(f"pool closed while sending {PER_CALL}"))

    with pytest.raises(RuntimeError) as caught:
        c.request("GET", "/api/data/v9.2/contacts", headers={"Authorization": f"Bearer {PER_CALL}"})

    assert PER_CALL not in shown(caught.value)
    assert "pool closed while sending" in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_per_call_header_echo_is_redacted_from_logs_during_the_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    c = dynamics()

    def send(*args: Any, **kwargs: Any):
        c._log.warning("upstream diagnostic: %s", PER_CALL)
        return response(200, {"value": []})

    c._session.request = Mock(side_effect=send)
    caplog.set_level(logging.WARNING)

    assert c.request("GET", "/x", headers={"Authorization": f"Bearer {PER_CALL}"}) == {"value": []}

    assert "upstream diagnostic" in caplog.text
    assert PER_CALL not in logged(caplog)


def test_per_call_header_echo_is_redacted_after_a_replayed_attempt() -> None:
    c = dynamics(attempts=2)
    c._session.request = Mock(side_effect=[response(503), response(400, echo_body(PER_CALL))])
    headers = {"Authorization": f"Bearer {PER_CALL}"}

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x", headers=headers)

    assert PER_CALL not in shown(caught.value)
    assert [call.kwargs["headers"] for call in c._session.request.call_args_list] == [headers, headers]


def test_per_call_header_echo_is_redacted_inside_the_nested_token_refresh() -> None:
    c = dynamics()
    c._client_secret = "dummy-client-secret-1846"
    c._scope = ["https://dynamics.example.test/.default"]
    seen_in_refresh: list[object] = []

    def acquire(*args: Any, **kwargs: Any) -> dict:
        # Inside the nested public refresh call: the outer call's per-call
        # value must already be in the redaction set here, not only when the
        # outer boundary re-sanitizes afterwards.
        seen_in_refresh.append(c._secret_values())
        return {"error_description": f"refresh refused while {PER_CALL} is active"}

    c._msal_app = SimpleNamespace(
        remove_tokens_for_client=Mock(),
        acquire_token_for_client=Mock(side_effect=acquire),
    )
    c._session.request = Mock(return_value=response(401))

    with pytest.raises(ConnectorAuthError) as caught:
        c.request("GET", "/x", headers={"Authorization": f"Bearer {PER_CALL}"})

    assert c._msal_app.acquire_token_for_client.called
    assert PER_CALL in seen_in_refresh[0]
    assert PER_CALL not in shown(caught.value)
    assert "refresh refused while" in str(caught.value)


# -- OAuth authorization codes ------------------------------------------------


@pytest.mark.parametrize("provider", ["hubspot", "salesforce", "zoho"])
def test_authorization_code_echo_is_redacted_from_the_token_exchange(provider: str) -> None:
    c = connector(provider)
    # Each provider reports a different field; all of them carry the echo.
    echo = f"code {CODE} has expired"
    c._session.post = Mock(return_value=response(400, {
        "message": echo, "error_description": echo, "error": echo,
    }))

    with pytest.raises(ConnectorAuthError) as caught:
        c.authenticate_with_code(CODE, CALLBACK)

    assert CODE not in shown(caught.value)
    assert "has expired" in str(caught.value)
    # The token request still sends the code unchanged.
    assert c._session.post.call_args.kwargs["data"]["code"] == CODE


@pytest.mark.parametrize("provider", ["hubspot", "salesforce", "zoho"])
def test_authorization_code_echo_is_redacted_at_the_public_error_boundary(provider: str) -> None:
    c = connector(provider)
    c._session.post = Mock(side_effect=RuntimeError(f"socket reset after sending {CODE}"))

    with pytest.raises(RuntimeError) as caught:
        c.authenticate_with_code(CODE, CALLBACK)

    assert CODE not in shown(caught.value)
    assert "socket reset after sending" in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_zoho_authorization_code_echo_in_a_200_error_body_is_redacted() -> None:
    # Zoho reports an invalid code as HTTP 200 with an "error" member.
    c = connector("zoho")
    c._session.post = Mock(return_value=response(200, {"error": f"code {CODE} is invalid"}))

    with pytest.raises(ConnectorAuthError) as caught:
        c.authenticate_with_code(CODE, CALLBACK)

    assert CODE not in shown(caught.value)
    assert "is invalid" in str(caught.value)


@pytest.mark.parametrize("provider", ["hubspot", "salesforce", "zoho"])
def test_a_non_text_authorization_code_fails_closed(provider: str) -> None:
    c = connector(provider)
    code = 31415926535897932
    echo = f"code {code} has expired"
    c._session.post = Mock(return_value=response(400, {
        "message": echo, "error_description": echo, "error": echo,
    }))

    with pytest.raises(ConnectorAuthError) as caught:
        c.authenticate_with_code(code, CALLBACK)

    assert str(code) not in shown(caught.value)
    assert str(caught.value) == "ConnectorAuthError"


# -- Short and uncollectable values fail closed -------------------------------


def test_short_per_call_credential_yields_only_the_trusted_constant() -> None:
    c = dynamics()
    c._session.request = Mock(return_value=response(400, echo_body(SHORT)))

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x", headers={"Authorization": f"Bearer {SHORT}"})

    assert SHORT not in shown(caught.value)
    assert str(caught.value) == "ConnectorError (HTTP 400)"


@pytest.mark.parametrize("provider", ["hubspot", "salesforce", "zoho"])
def test_short_authorization_code_yields_only_the_trusted_constant(provider: str) -> None:
    c = connector(provider)
    echo = f"code {SHORT} has expired"
    c._session.post = Mock(return_value=response(400, {
        "message": echo, "error_description": echo, "error": echo,
    }))

    with pytest.raises(ConnectorAuthError) as caught:
        c.authenticate_with_code(SHORT, CALLBACK)

    assert SHORT not in shown(caught.value)
    assert str(caught.value) == "ConnectorAuthError"


def test_logs_during_a_call_with_a_short_per_call_value_are_suppressed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    c = dynamics()

    def send(*args: Any, **kwargs: Any):
        c._log.warning("upstream diagnostic: %s", SHORT)
        return response(200, {})

    c._session.request = Mock(side_effect=send)
    caplog.set_level(logging.WARNING)

    c.request("GET", "/x", headers={"Authorization": f"Bearer {SHORT}"})

    assert caplog.records
    assert SHORT not in logged(caplog)
    assert "upstream diagnostic" not in caplog.text


def test_short_value_and_failed_collection_end_with_their_call() -> None:
    c = dynamics()
    ordinary = "Dynamics 400: Entity contacts does not support this filter"
    c._session.request = Mock(return_value=response(400, {
        "error": {"message": "Entity contacts does not support this filter"},
    }))

    with pytest.raises(ConnectorError) as short_call:
        c.request("GET", "/x", headers={"Authorization": f"Bearer {SHORT}"})
    with pytest.raises(ConnectorError) as next_call:
        c.request("GET", "/x")
    with pytest.raises(ConnectorError) as failed_call:
        c.request("GET", "/x", headers={"Authorization": 31415926535897932})
    with pytest.raises(ConnectorError) as last_call:
        c.request("GET", "/x")

    assert str(short_call.value) == "ConnectorError (HTTP 400)"
    assert str(failed_call.value) == "ConnectorError (HTTP 400)"
    assert str(next_call.value) == ordinary
    assert str(last_call.value) == ordinary


def test_a_non_text_credential_header_value_fails_closed() -> None:
    c = dynamics()
    value = 31415926535897932
    c._session.request = Mock(return_value=response(400, echo_body(str(value))))

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x", headers={"Authorization": value})

    assert str(value) not in shown(caught.value)
    assert str(caught.value) == "ConnectorError (HTTP 400)"
    assert c._session.request.call_args.kwargs["headers"] == {"Authorization": value}


ENCODED = "dummy/per+call=credential/1846"


@pytest.mark.parametrize("form", [ENCODED, quote(ENCODED, safe=""), quote_plus(ENCODED)],
                         ids=["raw", "percent-encoded", "form-encoded"])
def test_encoded_echoes_of_a_per_call_credential_are_redacted(form: str) -> None:
    c = dynamics()
    c._session.request = Mock(return_value=response(400, echo_body(form)))

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x", headers={"Authorization": f"Bearer {ENCODED}"})

    assert form not in shown(caught.value)
    assert "was rejected for this tenant" in str(caught.value)


class HostileHeaders(Mapping):
    """A caller mapping whose iteration fails with a credential in the error text."""

    def __getitem__(self, key: str) -> str:
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        raise RuntimeError(f"header store locked: {PER_CALL}")

    def __len__(self) -> int:
        return 1


def test_uncollectable_per_call_headers_yield_only_the_trusted_constant() -> None:
    c = dynamics()
    c._session.request = Mock(return_value=response(200, {}))

    with pytest.raises(RuntimeError) as caught:
        c.request("GET", "/x", headers=HostileHeaders())

    assert PER_CALL not in shown(caught.value)
    assert str(caught.value) == "RuntimeError"


# -- Positives: existing redaction and ordinary diagnostics are unchanged -----


def test_configured_and_session_credentials_are_still_redacted_with_per_call_headers() -> None:
    c = dynamics()
    configured = "dummy-configured-token-1846"
    session = "dummy-session-header-token-1846"
    c._access_token = configured
    c._session.headers["Authorization"] = f"Bearer {session}"
    c._session.request = Mock(return_value=response(400, {
        "error": {"message": f"tokens {configured} {session} {PER_CALL} rejected"},
    }))

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x", headers={"X-Api-Key": PER_CALL})

    for value in (configured, session, PER_CALL):
        assert value not in shown(caught.value)
    assert "rejected" in str(caught.value)


def test_non_credential_per_call_headers_do_not_suppress_ordinary_detail() -> None:
    c = dynamics()
    c._session.request = Mock(return_value=response(400, {
        "error": {"message": "Prefer return=representation is not supported on this entity"},
    }))

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x", headers={"Prefer": "return=representation"})

    assert str(caught.value) == (
        "Dynamics 400: Prefer return=representation is not supported on this entity"
    )


# -- Header shapes requests still sends ---------------------------------------


@pytest.mark.parametrize("headers", [
    {b"Authorization": f"Bearer {PER_CALL}"},
    {"Authorization": f"Bearer\t{PER_CALL}"},
    {"Authorization": f"Bearer {PER_CALL}".encode("latin-1")},
], ids=["bytes-name", "tab-after-scheme", "bytes-value"])
def test_other_credential_header_shapes_are_redacted(headers: dict) -> None:
    c = dynamics()
    c._session.request = Mock(return_value=response(401, echo_body(PER_CALL)))

    with pytest.raises(ConnectorAuthError) as caught:
        c.request("GET", "/x", headers=headers)

    assert PER_CALL not in shown(caught.value)
    assert "was rejected for this tenant" in str(caught.value)
    assert c._session.request.call_args.kwargs["headers"] == headers


class MintingHeaders(Mapping):
    """A caller mapping that returns a different credential on every read."""

    def __init__(self) -> None:
        self.reads = 0

    def __getitem__(self, key: str) -> str:
        if key != "Authorization":
            raise KeyError(key)
        self.reads += 1
        return f"Bearer {PER_CALL}-{self.reads}"

    def __iter__(self) -> Iterator[str]:
        return iter(["Authorization"])

    def __len__(self) -> int:
        return 1


def test_headers_are_read_once_so_every_sent_value_is_registered() -> None:
    c = dynamics(attempts=2)
    sent: list[str] = []

    def send(*args: Any, **kwargs: Any):
        sent.append(kwargs["headers"]["Authorization"])
        if len(sent) == 1:
            return response(503)
        return response(400, echo_body(sent[-1].split(" ", 1)[1]))

    c._session.request = Mock(side_effect=send)

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x", headers=MintingHeaders())

    assert len(sent) == 2 and sent[0] == sent[1]
    assert PER_CALL not in shown(caught.value)


def test_a_none_header_value_does_not_suppress_ordinary_detail() -> None:
    # requests drops a None-valued header, so nothing is sent and nothing is
    # registered; the ordinary upstream message stays.
    c = dynamics()
    c._session.request = Mock(return_value=response(400, {
        "error": {"message": "Entity contacts does not support this filter"},
    }))

    with pytest.raises(ConnectorError) as caught:
        c.request("GET", "/x", headers={"Authorization": None})

    assert str(caught.value) == "Dynamics 400: Entity contacts does not support this filter"


class HostileStr(str):
    """A credential whose own methods raise with the credential in the text."""

    def _boom(self, *args: Any) -> Any:
        raise RuntimeError(f"hostile credential {str.__str__(self)}")

    __eq__ = __len__ = __str__ = __bool__ = _boom
    __hash__ = str.__hash__


def test_a_str_subclass_header_value_is_registered_without_running_its_methods() -> None:
    c = dynamics()
    c._session.request = Mock(return_value=response(401, echo_body(PER_CALL)))
    value = HostileStr(f"Bearer {PER_CALL}")

    with pytest.raises(ConnectorAuthError) as caught:
        c.request("GET", "/x", headers={"Authorization": value})

    assert PER_CALL not in shown(caught.value)
    assert "was rejected for this tenant" in str(caught.value)
    assert c._session.request.call_args.kwargs["headers"]["Authorization"] is value


@pytest.mark.parametrize("provider", ["hubspot", "salesforce", "zoho"])
def test_a_str_subclass_authorization_code_is_registered_without_running_its_methods(
    provider: str,
) -> None:
    c = connector(provider)
    echo = f"code {CODE} has expired"
    c._session.post = Mock(return_value=response(400, {
        "message": echo, "error_description": echo, "error": echo,
    }))
    code = HostileStr(CODE)

    with pytest.raises(ConnectorAuthError) as caught:
        c.authenticate_with_code(code, CALLBACK)

    assert CODE not in shown(caught.value)
    assert c._session.post.call_args.kwargs["data"]["code"] is code


NON_ASCII = "dummy-per-call-crédential-1846"


@pytest.mark.parametrize("headers,echoed", [
    ({"Authorization ": f"Bearer {PER_CALL}"}, PER_CALL),
    ({"Authorization": f"Bearer {NON_ASCII}".encode("utf-8")}, NON_ASCII),
], ids=["name-with-trailing-space", "utf-8-bytes-value"])
def test_whitespace_names_and_utf8_byte_values_are_redacted(headers: dict, echoed: str) -> None:
    c = dynamics()
    c._session.request = Mock(return_value=response(401, echo_body(echoed)))

    with pytest.raises(ConnectorAuthError) as caught:
        c.request("GET", "/x", headers=headers)

    assert echoed not in shown(caught.value)
    assert "was rejected for this tenant" in str(caught.value)


@pytest.mark.parametrize("cls", [
    type(connector(provider)) for provider in ("dynamics", "hubspot", "salesforce", "zoho")
])
def test_crm_connectors_define_no_public_generator_or_async_methods(cls: type) -> None:
    # The per-call credential scope is opened by the sync and coroutine
    # boundaries. Generator, async-generator and coroutine public methods are
    # outside what these tests prove (a generator opens no scope of its own;
    # tasks spawned by a coroutine share its scope). Adding one must revisit
    # that design, so this fails until it does.
    import inspect

    offenders = []
    for name in dir(cls):
        if name.startswith("_"):
            continue
        attr = inspect.getattr_static(cls, name)
        funcs = [attr.fget, attr.fset, attr.fdel] if isinstance(attr, property) else [
            getattr(attr, "__func__", attr),
        ]
        for func in funcs:
            if func is None or not callable(func):
                continue
            func = inspect.unwrap(func)
            if (inspect.isgeneratorfunction(func) or inspect.isasyncgenfunction(func)
                    or inspect.iscoroutinefunction(func)):
                offenders.append(name)
    assert offenders == []


# -- Lifetime: registered for the call, forgotten afterwards ------------------


def test_per_call_value_is_registered_during_the_call_and_dropped_after_it() -> None:
    c = dynamics()
    during: list[object] = []

    def send(*args: Any, **kwargs: Any):
        during.append(c._secret_values())
        return response(200, {})

    c._session.request = Mock(side_effect=send)
    c.request("GET", "/x", headers={"Authorization": f"Bearer {PER_CALL}"})

    assert PER_CALL in during[0]
    assert PER_CALL not in c._secret_values()


def test_per_call_value_is_dropped_after_the_call_raises() -> None:
    c = dynamics()
    during: list[object] = []

    def send(*args: Any, **kwargs: Any):
        during.append(c._secret_values())
        return response(400, echo_body(PER_CALL))

    c._session.request = Mock(side_effect=send)

    with pytest.raises(ConnectorError):
        c.request("GET", "/x", headers={"Authorization": f"Bearer {PER_CALL}"})

    assert PER_CALL in during[0]
    assert PER_CALL not in c._secret_values()
    assert c._secret_values() == [c._access_token]


@pytest.mark.parametrize("provider", ["hubspot", "salesforce", "zoho"])
def test_authorization_code_is_registered_during_the_exchange_and_dropped_after(
    provider: str,
) -> None:
    c = connector(provider)
    during: list[object] = []

    def post(*args: Any, **kwargs: Any):
        during.append(c._secret_values())
        return response(400, {"message": "bad", "error": "bad", "error_description": "bad"})

    c._session.post = Mock(side_effect=post)

    with pytest.raises(ConnectorAuthError):
        c.authenticate_with_code(CODE, CALLBACK)

    assert CODE in during[0]
    assert CODE not in c._secret_values()
