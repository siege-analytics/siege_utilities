"""R-1846-4 close-the-class contract (#1846).

A committed AST check over the four CRM connectors. Exceptions are not routed
through the RedactingLogger, so any value interpolated into a ``raise`` (or into
an error-constructor message such as ``rate_limit_error(...)``) is emitted
verbatim. This test fails if any such interpolation is not a reviewed redactor
call (``_redact_field`` / ``_safe_upstream_detail`` / ``_extract_error``) or a
short explicit safe form: ``type(exc).__name__``, an HTTP ``.status_code``, an
ALL-CAPS module constant, or a reviewed non-credential bare name (HTTP verb /
integer counter). It also requires every ``self._log.*`` call to use a literal
message template, so the logger can value-redact the separate arguments.

A caller-supplied field (``object_type`` / ``entity_set`` / ``job_id``) is not
safe merely by its name: it reaches this check as a bare parameter and fails
until wrapped. The source is parsed, never imported, so the check runs without
the optional transport dependencies (requests, msal, duckdb).
"""
import ast
from pathlib import Path

import pytest

CONNECTOR_DIR = Path(__file__).resolve().parents[1] / "siege_utilities" / "connectors"
CONNECTORS = ["salesforce.py", "hubspot.py", "zoho.py", "dynamics.py"]

# Calls whose result is already value-redacted / short-credential-suppressed.
REDACTORS = {"_redact_field", "_safe_upstream_detail", "_extract_error"}
# Bare names that are reviewed non-credential diagnostics: the HTTP verb,
# integer counters, an integer HTTP status code, and the Zoho data-center enum
# that a config ValueError echoes back to the caller (it is validated against a
# fixed set and carries no credential). A caller object/entity type is NOT on
# this list -- it reaches the check as a bare parameter and fails until wrapped.
SAFE_BARE_NAMES = {
    "method", "attempt", "attempts", "total", "processed", "failed",
    "elapsed", "succeeded", "count", "status", "data_center",
}
# Attribute leaves that are trusted: exception/type names and HTTP status ints.
SAFE_ATTRS = {"__name__", "status_code"}
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical"}


def _assignments(func):
    """Map name -> RHS expressions assigned in this function's own body."""
    out = {}

    def visit(nodes):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue  # a nested scope cannot bind this function's names
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        out.setdefault(target.id, []).append(node.value)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
                out.setdefault(node.target.id, []).append(node.value)
            elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
                out.setdefault(node.target.id, []).append(node.value)
            visit(list(ast.iter_child_nodes(node)))

    visit(list(func.body))
    return out


def _is_safe(node, assigns, seen):
    """A value interpolated into an exception message is reviewed-safe."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.JoinedStr):
        return all(
            _is_safe(part.value, assigns, seen)
            for part in node.values
            if isinstance(part, ast.FormattedValue)
        )
    if isinstance(node, ast.FormattedValue):
        return _is_safe(node.value, assigns, seen)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_safe(node.left, assigns, seen) and _is_safe(node.right, assigns, seen)
    if isinstance(node, ast.IfExp):
        return _is_safe(node.body, assigns, seen) and _is_safe(node.orelse, assigns, seen)
    if isinstance(node, ast.Attribute):
        return node.attr in SAFE_ATTRS
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Attribute):
            return False
        if node.func.attr in REDACTORS:
            return True
        # A method on a trusted receiver with trusted arguments, e.g.
        # ", ".join(ZOHO_DATA_CENTERS.keys()). An upstream receiver (self._raw(),
        # job_info.get(...)) is not safe because the receiver is not safe.
        return (
            _is_safe(node.func.value, assigns, seen)
            and all(_is_safe(arg, assigns, seen) for arg in node.args)
            and all(_is_safe(kw.value, assigns, seen) for kw in node.keywords)
        )
    if isinstance(node, ast.Name):
        if node.id.isupper() or node.id in SAFE_BARE_NAMES:
            return True
        if node.id in assigns and node.id not in seen:
            return all(_is_safe(rhs, assigns, seen | {node.id}) for rhs in assigns[node.id])
        return False
    return False


def _message_strings(node, assigns, seen, acc):
    """Collect JoinedStr nodes reachable as the exception/error message."""
    if node is None:
        return
    if isinstance(node, ast.JoinedStr):
        acc.append(node)
        return
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        _message_strings(node.left, assigns, seen, acc)
        _message_strings(node.right, assigns, seen, acc)
        return
    if isinstance(node, ast.IfExp):
        _message_strings(node.body, assigns, seen, acc)
        _message_strings(node.orelse, assigns, seen, acc)
        return
    if isinstance(node, ast.Call):
        for arg in node.args:
            _message_strings(arg, assigns, seen, acc)
        return
    if isinstance(node, ast.Name) and node.id in assigns and node.id not in seen:
        for rhs in assigns[node.id]:
            _message_strings(rhs, assigns, seen | {node.id}, acc)


def _is_log_call(node):
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in LOG_METHODS
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "_log"
    )


def violations(source, label):
    """Return a list of contract violations in one connector source string."""
    tree = ast.parse(source)
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    def enclosing_func(node):
        cur = node
        while cur in parents:
            cur = parents[cur]
            if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return cur
        return None

    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            func = enclosing_func(node)
            assigns = _assignments(func) if func else {}
            acc = []
            _message_strings(node.exc, assigns, set(), acc)
            for joined in acc:
                for part in joined.values:
                    if isinstance(part, ast.FormattedValue) and not _is_safe(part.value, assigns, set()):
                        found.append(
                            f"{label}:{part.value.lineno} raise interpolates "
                            f"unredacted {ast.unparse(part.value)}"
                        )
        elif isinstance(node, ast.Call) and _is_log_call(node):
            template = node.args[0] if node.args else None
            if not (isinstance(template, ast.Constant) and isinstance(template.value, str)):
                shown = ast.unparse(template) if template is not None else "<no args>"
                found.append(f"{label}:{node.lineno} log template is not a literal: {shown}")
    return found


@pytest.mark.parametrize("name", CONNECTORS)
def test_connector_raises_and_logs_never_interpolate_unredacted_values(name):
    source = (CONNECTOR_DIR / name).read_text(encoding="utf-8")
    found = violations(source, name)
    assert not found, "unredacted connector interpolations:\n" + "\n".join(found)


# -- The checker itself: prove it goes red on the exact F1/F2 class, and that a
# redacted sibling is accepted (no false positive). This is the committed
# plant-one-red proof.
_RAW_RAISE = (
    "class C:\n"
    "    def create_record(self, object_type):\n"
    "        raise ConnectorError(f'Failed to create {object_type}')\n"
)
_REDACTED_RAISE = (
    "class C:\n"
    "    def create_record(self, object_type):\n"
    "        raise ConnectorError(f'Failed to create {self._redact_field(object_type)}')\n"
)
_RAW_LOG = (
    "class C:\n"
    "    def go(self, object_type):\n"
    "        self._log.info(f'Created {object_type}')\n"
)


def test_checker_flags_a_raw_caller_value_interpolation():
    assert violations(_RAW_RAISE, "synthetic") != []


def test_checker_accepts_a_redacted_interpolation():
    assert violations(_REDACTED_RAISE, "synthetic") == []


def test_checker_flags_a_non_literal_log_template():
    assert violations(_RAW_LOG, "synthetic") != []
