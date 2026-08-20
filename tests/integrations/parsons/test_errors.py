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

    def test_429_with_unparseable_retry_after(self) -> None:
        mapped = map_parsons_exception(_http_error(429, retry_after="Mon, 01 Jan 2027 00:00:00 GMT"), connector="van")
        assert isinstance(mapped, ConnectorRateLimitError)
        # HTTP-date form is not parsed; retry_after is None rather than raising.
        assert mapped.retry_after is None

    def test_500_maps_to_generic_connector_error(self) -> None:
        mapped = map_parsons_exception(_http_error(500), connector="van")
        assert isinstance(mapped, ConnectorError)
        assert not isinstance(mapped, (ConnectorAuthError, ConnectorNotFoundError, ConnectorRateLimitError))

    def test_generic_exception_without_response_attr(self) -> None:
        mapped = map_parsons_exception(ValueError("bad input"), connector="action_kit")
        assert isinstance(mapped, ConnectorError)
        assert "ValueError" in str(mapped)
        assert "[action_kit]" in str(mapped)

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
