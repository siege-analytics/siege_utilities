# Design note — #801: credential_manager returns None on total backend failure

## Step 1 — Context

`siege_utilities/config/credential_manager.py` exposes
`CredentialManager.get_credential()` and a module-level `get_credential()` wrapper. The method
iterates `backend_priority` (`files`, `env`, `1password`, `keychain`, `prompt`), calling a
per-backend helper. Each helper returns `None` when the credential is legitimately
absent from that backend, and raises on transport/auth failures (already fixed in a prior
ticket). When the loop completes with no value, the method logs a warning and `return None`
(line 261). Module-level wrapper at line 807 propagates that None.

This is an SU-1 violation: "errors are not data." A caller has no way to distinguish
"credential genuinely not configured anywhere" from "1Password CLI raised but we caught and
moved on" (actually: per-backend raises propagate now, but the no-credential-found
endstate still returns a value-shaped None). The aggregate must signal absence as an error.

### Sibling-grep (mandatory for fix tasks)

Searched the codebase for siblings — aggregate functions that walk multiple sources and
end with `return None` on total miss. Within `credential_manager.py`:

| Function | Pattern | Status |
|---|---|---|
| `CredentialManager.get_credential` (line 261) | iterates backends, returns None | **this ticket** |
| `CredentialManager.get_google_analytics_credentials` (line 622) | tries 1Password by-title then general lookup, returns None | aggregate; already logs error; wraps in try/except Exception |
| `get_ga_service_account_credentials` (line 1004) | calls `get_credential` 4×, returns None on any miss | aggregate; NOT wrapped — relies on get_credential returning None |
| `get_google_service_account_from_1password` (line 1035) | single backend, returns None on CalledProcessError | single-source — not a fallback aggregate |
| `get_google_oauth_from_1password` (line 1095) | single backend | single-source |
| `get_google_oauth_document_from_1password` (line 1167) | single backend | single-source |

N=2 same-shape aggregates besides the ticket's target (`get_google_analytics_credentials`,
`get_ga_service_account_credentials`). Combined with the ticket = N=3 → writing-rules:7
hard gate. Decision: **fix #801 as scoped (aggregate `get_credential`), file follow-up
tickets for the two Google-specific aggregates.** I will not silently expand scope —
the ticket names a specific function and a specific contract; the siblings need their
own tickets so callers of those helpers can be audited independently (their current
behavior is documented as "returns None or tuple/dict").

The two siblings will get a one-line note in the self-review artifact and a `TODO(#801-followup)`
comment near each, naming the follow-up. (No new ticket creation in this session — per
batch-execution discipline, separate tickets = separate `think` gates.)

Outside `credential_manager.py`: I scanned `data_source_registry.py:188` — that
`get_credential` is dict lookup, not a fallback chain. Not a sibling.

### Callers of `get_credential` to audit

Internal to `credential_manager.py`:
- L607 `self.get_credential(...)` — verification probe inside `store_google_analytics_credentials`. If it raises, the function should return False (storage failure to verify).
- L641–642 inside `get_google_analytics_credentials` — already in `try/except Exception → return None`. Will catch `CredentialNotFoundError` and preserve its API.
- L982 inside `store_ga_service_account_from_file` — already in outer `try/except Exception → return False`. Preserved.
- L1014–1021 inside `get_ga_service_account_credentials` — **NOT wrapped**. Needs `try/except CredentialNotFoundError → return None` so its docstring contract ("Returns Dict … or None") holds. Or `if not client_email: return None` already catches the first miss path; but raising changes that. Will catch explicitly.

External:
- `siege_utilities/config/__init__.py` re-exports `get_credential`. Need to also export `CredentialNotFoundError`.
- `analytics/google_analytics.py`, `analytics/google_workspace.py`, `reporting/examples/google_analytics_report_example.py` — none of these call `get_credential` directly; they call `get_google_service_account_from_1password` / `get_google_oauth_from_1password`, which are unchanged.
- `notebooks/archive/03_Person_Actor_Architecture.ipynb` — archived per CLAUDE.md, not actively maintained, not in scope.
- `tests/test_credential_manager.py` — has `test_returns_none_when_all_fail` (line 606) that must be updated to `test_raises_when_all_fail`. Several test_returns_none_… tests on internal `_get_from_*` helpers stay as-is (per-backend contract unchanged).

## Step 2 — Questions / Assumptions

- **Assumption**: `CredentialNotFoundError` is a new exception class. No existing exception
  in the package fits. It belongs in `credential_manager.py` next to its sole raiser, and
  is re-exported from `siege_utilities.config` for catch sites.
- **Assumption**: Error message should list each backend attempted and the outcome
  ("not found" / skipped because unavailable). Backend transport errors already raise
  earlier and short-circuit the loop — they never reach the new raise site, so message
  enumerates only the "fall through" path.
- **Assumption**: Inheriting from `LookupError` is correct semantically (credential lookup
  failed) and gives callers who don't import the specific class a useful base class.
- **Assumption**: The two sibling aggregates are out of scope for this ticket. TODO comments
  reference #801 follow-up; no new tickets created in this session.

## Step 3 — Proposals

| Approach | What | Tradeoff |
|---|---|---|
| **A. Raise `CredentialNotFoundError(LookupError)` from `get_credential`** (recommended) | New exception subclass of LookupError; track per-backend outcome dict; raise with formatted message at the end | Breaking change for callers that test `is None`; matches SU-1; small surface |
| B. Add `get_credential_or_raise` sibling | Keep `get_credential` returning None; add new strict variant | Avoids breakage but multiplies the API; the existing function still violates SU-1 |
| C. Return a sentinel object (`NotFound`) instead of None | Lets callers distinguish without try/except | Adds a new vocabulary, doesn't propagate context, still value-shaped |

**Choosing A**: the ticket explicitly names the fix direction; this is the SU-1-correct
shape; the breakage surface is contained (5 internal call sites + 1 test, all updated
in this PR).

## Step 4 — Design

### New exception

```python
class CredentialNotFoundError(LookupError):
    """Raised when no configured backend yields the requested credential.

    Distinct from backend transport / auth errors, which propagate from the
    per-backend helpers. Carries per-backend attempt outcomes so callers can
    surface actionable diagnostics.
    """
    def __init__(self, service: str, field: str, attempts: list[tuple[str, str]]):
        self.service = service
        self.field = field
        self.attempts = attempts  # list of (backend_name, outcome_str)
        lines = "\n".join(f"  - {b}: {o}" for b, o in attempts)
        super().__init__(
            f"Could not retrieve {field!r} for {service!r} from any backend.\n"
            f"Backends tried:\n{lines}"
        )
```

### Modified `CredentialManager.get_credential`

- Build `attempts: list[tuple[str, str]]` over the loop.
- For each backend in `backend_priority`: if unavailable → record `(name, "skipped: backend unavailable")`; else dispatch and record `(name, "no credential")` on None return.
- Backend raises propagate (unchanged).
- After loop: log_warning (kept) and `raise CredentialNotFoundError(service, field, attempts)`.

### Modified internal callers

- `store_google_analytics_credentials` (line 607): wrap verify probe in `try/except CredentialNotFoundError`, return False on miss with log_warning (current behavior is `return False` already; just change the trigger).
- `get_ga_service_account_credentials` (line 1014): wrap the 4 `manager.get_credential` calls in a single try/except that returns None.
- `store_ga_service_account_from_file` (line 982): already in big `except Exception`; CredentialNotFoundError (LookupError) inherits from Exception, will be caught. Keep.
- `get_google_analytics_credentials` (line 641-642): already in `except Exception`. Keep.

### Module-level

- `get_credential()` function (line 807): no body change; raise propagates.
- `siege_utilities/config/__init__.py`: add `CredentialNotFoundError` to imports and `__all__`.

### Tests

- Update `test_returns_none_when_all_fail` → `test_raises_when_all_fail`, assert `with pytest.raises(CredentialNotFoundError)`.
- Add `test_raise_includes_backend_attempts`: error message contains each backend name.
- Add `test_unavailable_backends_marked_skipped`: when 1password unavailable, attempts list reflects that.
- `test_returns_none_on_exception` for `get_google_analytics_credentials` — still passes (Exception base catches LookupError).

## Step 5 — Documentation Plan

- Docstring of `CredentialManager.get_credential`: update return doc to "Returns credential value. Raises CredentialNotFoundError if no backend yields the credential. Backend transport errors propagate from helpers."
- Same for module-level `get_credential`.
- No notebook impact (archive notebook only).
- CHANGELOG entry: add to unreleased section noting breaking change with migration snippet.

## Step 6 — Implementation Gate

User has given detailed instructions in the task body specifying the fix direction
(`CredentialNotFoundError` with backend list). Proceed under the think-skill exemption
"Tasks where the user has given detailed, specific, step-by-step instructions".

## Investigation Dependencies

- Verified callers above by grep. If a downstream caller in a different repo depends on
  `None` return, this is a breaking change documented in the PR.
- Verified test file structure — only `test_credential_manager.py` and the OAuth fallback
  tests reference these symbols.
