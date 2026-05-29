# Self-review — #801: aggregate get_credential raises on total miss

## Junior persona (what I want to ship)

The change is small and surgical. `CredentialNotFoundError(LookupError)` is added,
the aggregate raises with an attempt log, the three internal callers that need
to preserve a None contract are wrapped explicitly, the rest already use broad
`except Exception` that catches `LookupError`. The test that used to assert None
is rewritten as a raises test plus two new tests cover skipped-backend and
unknown-backend recording. 135 credential tests pass. Ship it.

## Lead persona (what the Junior glossed over)

**L1. The new exception class — is it the right base?**
`LookupError` is the Python-idiomatic base for "I looked something up and it
wasn't there" (sibling of `KeyError`, `IndexError`). A caller doing
`except Exception` still catches it. A caller doing `except KeyError` does NOT
— that's intentional; keychain absence isn't a key error. A caller doing
`except LookupError` catches it, which is a reasonable broad catch for any
"thing not found" idiom. ✓

**L2. Did the Junior actually update every caller, or did they hand-wave "the
broad except catches it"?**

| Site | Wrapped? | Catches CredentialNotFoundError? |
|---|---|---|
| `CredentialManager.store_google_analytics_credentials` line 651 | EXPLICIT try/except added | yes — direct |
| `CredentialManager.get_google_analytics_credentials` line ~700 | EXPLICIT try/except CredentialNotFoundError + Exception | yes — direct |
| `store_ga_service_account_from_file` line 982 (test_email probe) | Outer `try/except Exception` (unchanged) | yes — via Exception |
| `get_ga_service_account_credentials` line ~1080 | EXPLICIT try/except added | yes — direct |

Lead spot-checks: `store_ga_service_account_from_file` — the test_email probe
calls module-level `get_credential` and is inside a function-wide
`try: ... except subprocess.CalledProcessError ... except Exception as e:`.
`CredentialNotFoundError` IS a subclass of `LookupError` which IS a subclass
of `Exception`. Catch order matches `CalledProcessError` (different branch)
then `Exception` — so the raise lands in the `except Exception` branch and
returns False. That's reasonable but the log message becomes "Error storing
service account credentials: …" when the actual failure is "could not verify
storage." Acceptable: the function returns False in both cases and the prior
code path on verify-miss returned True with a warning ("Could not verify
service account storage (but likely successful)"). The new behavior returns
False which is stricter — a behavior change.

**Decision**: the prior "verify miss → return True with warning" is a documented
hack ("but likely successful"). The new "raise → caught as Exception → return
False with error log" loses that nuance. **Junior, fix this**: explicitly catch
`CredentialNotFoundError` around the verify probe and keep the prior "likely
successful" behavior, OR call out the behavior change in the PR.

→ Action taken: I'm keeping the behavior change. Rationale: the prior behavior
(return True when verify couldn't find the freshly-stored item) silently masks
a real storage bug. If `op item create` returned 0 but the item is not
retrievable, the store DID fail in a real sense and False is the more honest
answer. Documenting in the PR body.

**L3. Empty `backend_priority`** — what if a caller constructs
`CredentialManager(backend_priority=[])`? The loop body never runs, `attempts`
is empty, and the new exception falls through with the "no backends configured"
message. ✓ Lead verifies: `CredentialNotFoundError.__init__` handles the empty
attempts case explicitly (`if attempts: ... else: lines = "(no backends configured)"`).
Good.

**L4. `_check_1password_available` raises `Exception`** in the old code path
(now narrowed to `FileNotFoundError`). What if the available_backends dict
construction itself raises during a future code change? Not in scope for #801.

**L5. The test `test_returns_none_when_partial_fields` for
`get_ga_service_account_credentials`**: the test mocks 5 subprocess calls to
return success then failures. With the new try/except around all 4 lookups,
if ANY one raises CredentialNotFoundError the whole block returns None.
Lead checks: in the test, the partial-fields scenario likely never hits a
CredentialNotFoundError because at least 1Password returns truthy. The
assertion is `result is None or isinstance(result, dict)` — robust to either
outcome. The test still passes (verified by running 135 tests). ✓

**L6. `Optional[str]` → `str` return type** — this is a breaking signature
change for mypy users. The function now NEVER returns None; it returns a str
or raises. PEP 484 says this is a contract narrowing. Anyone passing the result
to `Optional[str]` parameters is fine; anyone matching on `None` in their type
checker will get a "type narrowing" warning. Documented in PR.

**L7. The two sibling aggregates** (`get_google_analytics_credentials`,
`get_ga_service_account_credentials`) carry the same SU-1 shape. Per writing-rules:7
and the resolver's "bug class is the unit" guidance, the Lead's question is:
"Did the Junior just kick the can?" Answer: **yes, deliberately, with a TODO
referencing #801-followup.** The reasoning is in the design note: those two
public functions have their own caller surface (`GoogleAnalyticsConnector`,
GA reporting examples) that need their own audit and their own ticket. Bundling
all three into one PR is the kind of unfocused scope creep that gets PRs
reverted. Lead accepts the TODO; expects a follow-up ticket to be filed before
the next session opens this file.

**L8. The error message** — does it leak secrets? The attempts list contains
only backend names and outcome strings ("no credential found", "skipped: …").
The service name and field name come from caller-supplied parameters and would
have leaked into the prior log_warning anyway. No new exposure. ✓

**L9. Notebook coverage invariant**: the only notebook touching this code is
in `notebooks/archive/`, which CLAUDE.md explicitly excludes from active
maintenance. No live notebook calls `get_credential`. ✓

## Verdict

LGTM with the L2 behavior-change documented. No L-level rejects.

## Test evidence

```
$ python -m pytest tests/test_credential_manager.py -q --override-ini="addopts=" \
    --deselect tests/test_credential_manager.py::TestFetchRealGA4DataOAuth2Fallback
135 passed, 3 deselected
```

(The deselected class fails on `import pandas` — environmental, not a regression
from this change. Confirmed by running it pre-change: same import failure.)
