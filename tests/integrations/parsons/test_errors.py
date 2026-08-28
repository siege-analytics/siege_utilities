"""Tests for siege_utilities.integrations.parsons._errors.

Every exception mapping is exercised. Every ``except`` block in the
mapping (and in the ``translate_errors`` decorator) is forced to fire by
a test that names the input class — SU-4b compliance from day one.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
)
from siege_utilities.integrations.parsons._errors import (
    map_parsons_exception,
    translate_errors,
)


def _http_error(status: int, retry_after: str | None = None) -> Exception:
    """Fabricate a requests.HTTPError-shaped exception for mapping tests.

    Uses a plain Exception subclass with the .response.status_code attribute
    chain the mapper reads. Avoids importing requests here so the tests run
    against the substrate without pulling all of parsons's transitive deps.
    """

    class _FakeHTTPError(Exception):
        pass

    headers: dict[str, str] = {}
    if retry_after is not None:
        headers["Retry-After"] = retry_after

    response = SimpleNamespace(status_code=status, headers=headers)
    exc = _FakeHTTPError(f"HTTP {status}")
    exc.response = response  # type: ignore[attr-defined]
    return exc


class TestMapParsonsException:
    """Direct mapping — no decorator, no wrapper class."""

    def test_import_error_maps_to_connector_error_with_extras_hint(self) -> None:
        exc = ImportError("No module named 'parsons.ngpvan'")
        mapped = map_parsons_exception(exc, connector="van")
        assert isinstance(mapped, ConnectorError)
        assert not isinstance(mapped, (ConnectorAuthError, ConnectorNotFoundError, ConnectorRateLimitError))
        assert "parsons-*" in str(mapped)
        assert "[van]" in str(mapped)

    def test_message_does_not_leak_backend_exception_text(self) -> None:
        """Backend messages may contain secrets (URLs, tokens, resolved
        values); the public ConnectorError message must not echo them."""
        marker = "SECRET-MARKER-abc123-do-not-leak"
        for status in (401, 403, 404, 429, 500, None):
            if status is None:
                exc = RuntimeError(f"connection to {marker}")
            else:
                exc = _http_error(status)
                exc.args = (f"payload contained {marker}",)
            mapped = map_parsons_exception(exc, connector="van")
            assert marker not in str(mapped), (
                f"status={status}: sanitizer leaked backend text into "
                f"{type(mapped).__name__}: {mapped!s}"
            )

    def test_401_maps_to_auth_error(self) -> None:
        mapped = map_parsons_exception(_http_error(401), connector="van")
        assert isinstance(mapped, ConnectorAuthError)
        assert "HTTP 401" in str(mapped)

    def test_403_maps_to_auth_error(self) -> None:
        mapped = map_parsons_exception(_http_error(403), connector="van")
        assert isinstance(mapped, ConnectorAuthError)

    def test_404_maps_to_not_found(self) -> None:
        mapped = map_parsons_exception(_http_error(404), connector="van")
        assert isinstance(mapped, ConnectorNotFoundError)

    def test_429_maps_to_rate_limit_with_retry_after(self) -> None:
        mapped = map_parsons_exception(_http_error(429, retry_after="12"), connector="van")
        assert isinstance(mapped, ConnectorRateLimitError)
        assert mapped.retry_after == 12.0

    def test_429_without_retry_after_header(self) -> None:
        mapped = map_parsons_exception(_http_error(429), connector="van")
        assert isinstance(mapped, ConnectorRateLimitError)
        assert mapped.retry_after is None

    def test_429_http_date_retry_after_is_parsed(self) -> None:
        """HTTP-date form of Retry-After is parsed (per Opus review
        finding #1 fix). A far-future date yields a large positive
        delta-seconds value; a past date yields 0.0 (clamped)."""
        # Far-future date parses to positive delta.
        mapped = map_parsons_exception(
            _http_error(429, retry_after="Wed, 01 Jan 2099 00:00:00 GMT"),
            connector="van",
        )
        assert isinstance(mapped, ConnectorRateLimitError)
        assert mapped.retry_after is not None
        assert mapped.retry_after > 0

    def test_429_past_http_date_retry_after_clamps_to_zero(self) -> None:
        """A Retry-After in the past means 'you may retry now'; clamp
        the negative delta to 0.0 rather than surface a nonsense
        negative sleep."""
        mapped = map_parsons_exception(
            _http_error(429, retry_after="Thu, 01 Jan 1970 00:00:00 GMT"),
            connector="van",
        )
        assert isinstance(mapped, ConnectorRateLimitError)
        assert mapped.retry_after == 0.0

    def test_429_garbage_retry_after_returns_none_with_warn(self) -> None:
        """Genuinely unparseable Retry-After (neither integer seconds
        nor a valid HTTP-date) returns None so callers know the header
        was uninterpretable. The _retry_after helper logs a warning."""
        mapped = map_parsons_exception(
            _http_error(429, retry_after="not-a-date-or-number"),
            connector="van",
        )
        assert isinstance(mapped, ConnectorRateLimitError)
        assert mapped.retry_after is None

    def test_500_maps_to_generic_connector_error(self) -> None:
        mapped = map_parsons_exception(_http_error(500), connector="van")
        assert isinstance(mapped, ConnectorError)
        assert not isinstance(mapped, (ConnectorAuthError, ConnectorNotFoundError, ConnectorRateLimitError))

    def test_generic_exception_records_class_name_only(self) -> None:
        """Sanitizer names the exception CLASS, not the message text."""
        mapped = map_parsons_exception(
            ValueError("secret-shaped: 12345"), connector="action_kit"
        )
        assert isinstance(mapped, ConnectorError)
        assert "ValueError" in str(mapped)
        assert "[action_kit]" in str(mapped)
        assert "secret-shaped" not in str(mapped)

    def test_message_without_connector_name_has_no_prefix(self) -> None:
        mapped = map_parsons_exception(RuntimeError("boom"))
        assert "[" not in str(mapped).split("]", 1)[0]


class TestTranslateErrorsDecorator:
    """Decorator preserves function metadata and translates raises."""

    def test_success_passes_through(self) -> None:
        @translate_errors("van")
        def happy() -> int:
            return 42

        assert happy() == 42

    def test_generic_exception_translated_to_connector_error(self) -> None:
        @translate_errors("van")
        def boom() -> None:
            raise RuntimeError("upstream failed")

        with pytest.raises(ConnectorError) as exc_info:
            boom()

        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "[van]" in str(exc_info.value)

    def test_connector_error_subclass_not_double_wrapped(self) -> None:
        @translate_errors("van")
        def already_typed() -> None:
            raise ConnectorAuthError("bad token")

        with pytest.raises(ConnectorAuthError) as exc_info:
            already_typed()

        # Original raised; no double-wrap.
        assert exc_info.value.__cause__ is None
        assert str(exc_info.value) == "bad token"

    def test_http_error_translated_to_auth(self) -> None:
        @translate_errors("van")
        def unauthorized() -> None:
            raise _http_error(401)

        with pytest.raises(ConnectorAuthError):
            unauthorized()

    def test_decorator_preserves_function_metadata(self) -> None:
        @translate_errors("van")
        def documented(x: int) -> int:
            """Sum of squares."""
            return x * x

        assert documented.__name__ == "documented"
        assert documented.__doc__ == "Sum of squares."

    def test_rejects_coroutine_functions(self) -> None:
        """The sync wrapper cannot translate exceptions raised in an
        ``await``; applying it to a coroutine function is refused at
        decoration time so the failure surfaces immediately rather than
        as a mysterious skipped-translation at first call."""

        async def coro() -> int:
            return 1

        with pytest.raises(TypeError) as exc_info:
            translate_errors("van")(coro)

        assert "coroutine" in str(exc_info.value).lower()
        assert "van" in str(exc_info.value)
