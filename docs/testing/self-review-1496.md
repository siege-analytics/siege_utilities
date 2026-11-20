# Self-review: expiry validators and model reload (#1496, PR #1805)

Scope of this artifact: the PR as a whole at its code head 5f863c01, plus the process-only commit that syncs with develop, adds the release note to `CHANGELOG.md` under `[4.1.0]` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code. The PR body was also refreshed.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at an earlier head by the external reviewer.

## Assumptions

- Goal source: ticket #1496. Persisted config models fail to reload once their expiry passes because four field validators reject past datetimes on every construction. The PR removes those validators; datetime parsing and validation stay in Pydantic.
- Scope: the PR references the ticket with `Refs`, not a closing keyword. The timezone-expiry crash noted in the ticket is ticket debt, not a regression introduced here, and this PR does not claim to fix it. The ticket scope is preserved.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the earlier verdict on the ticket and PR.
- The code diff against `origin/develop` after the sync is `siege_utilities/config/models/actor_types.py`, `credential.py`, `oauth_integration.py`, `tests/test_1496_expiry_validators_reload.py` and `tests/test_config_models_actor_types_errors.py`, plus `CHANGELOG.md` from this commit. This commit adds no library code.
- Release convention: user-visible notes belong in `CHANGELOG.md` under `[4.1.0]`. Before this commit the #1496 note existed only in the PR body block, although the body text said it was in the existing section; this commit adds it to `CHANGELOG.md` verbatim from that block.
- Pre-author-inventory: NONE. Trivial-against-state: after the sync, `git diff origin/develop -- CHANGELOG.md` shows only the #1496 entry as an addition.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree after the sync, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_1496_expiry_validators_reload.py test_config_models_actor_types_errors.py test_config_model_validation.py` -> 120 passed in 0.35s.
- Hosted CI at the pushed head is recorded in the PR body once it finishes.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has the #1496 entry under `[4.1.0]` Fixed exactly once.
- Request a fresh exact-head review: any earlier result is void once the head moves, and the code diff against develop is unchanged.

## Pre-flight (develop 71f02b0b)

Develop was merged additively. The only conflict was `CHANGELOG.md`; every develop line was kept. Develop wins on any disagreement, and none exists: no develop change touches `siege_utilities/config/models/`.

Classification: constructing one of the four models with a past expiry used to raise a validation error and no longer does, so caller code that relied on that rejection behaves differently. Per the standing rule the entry is now under `### BREAKING` in `[4.1.0]` with a Migration line, at its own position in the BREAKING list so it does not conflict with the other open PRs. This is a judgment call and is flagged to the reviewer: if the reviewer reads loosening a validator as non-breaking, the entry can move back to Fixed without any code change. The PR body classification is updated to match.

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_1496_expiry_validators_reload.py test_config_models_actor_types_errors.py test_config_model_validation.py -q` -> 120 passed in 0.41s. The library code is unchanged since the red/green run recorded in the Falsification entry below, which still applies to this head.

## Ticket-fitness exemption

Governing ticket: #1496 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1496 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (four future-only expiry validators rejecting past datetimes, so persisted models fail to reload after expiry), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1496, and in the PR description, https://github.com/siege-analytics/siege_utilities/pull/1805. The reviewer verdicts are recorded on the ticket thread and the PR conversation. With the timezone round below, every Done-when item maps to a test, and this PR closes the ticket with `Fixes`.
- **Falsification:** revert the implementation (removal of the four validators in `actor_types.py`, `credential.py` and `oauth_integration.py`); `tests/test_1496_expiry_validators_reload.py::test_expired_credential_reloads` goes red because construction raises the future-only validation error. Observed revert run: with `siege_utilities/config/models/actor_types.py`, `credential.py` and `oauth_integration.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/config/models/actor_types.py siege_utilities/config/models/credential.py siege_utilities/config/models/oauth_integration.py`), `python -m pytest test_1496_expiry_validators_reload.py::test_expired_credential_reloads -q`, run from the tests directory, gave 1 failed in 0.21s (pydantic `ValidationError`, value_error, from the future-only validator). After `git checkout HEAD --` of the files the command gave 1 passed in 0.19s, `test_1496_expiry_validators_reload.py` with `test_config_models_actor_types_errors.py` gave 14 passed on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Timezone round

Probe at `ad7613c8`: `Credential(..., expires_at="2099-01-01T00:00:00Z")` constructed, but `is_expired()` and `is_valid()` raised `TypeError: can't compare offset-naive and offset-aware datetimes`. So `Person.get_valid_credentials()` would crash on such a credential, and #1496 Done-when items 2 and 3 (normalisation and the `Z` case) were unmet.

Fix: `siege_utilities/config/models/_expiry.py` adds `as_utc` and `utc_now`. Every expiry comparison now goes through them:
- `Credential.is_expired`;
- `OAuthIntegration.is_token_expired` and `needs_refresh`;
- `Collaborator.is_access_expired`;
- `Collaboration.is_active`.

Aware values compare as instants. Naive values are local wall-clock time: the config models use naive `datetime.now()` throughout (`update_tokens`, `extend_access`, default timestamps), and v4.0.0 compared naive values against naive local `now()`, so a naive expiry keeps its v4.0.0 instant. Storage contract (documented in `_expiry.py`): values are stored as given and compared as instants through the helper. A naive value stays naive. A value supplied aware (for example ending in `Z`) stays aware on the attribute, which is not a regression, because v4.0.0 could not construct such a value. A grep of `config/models` finds no other `datetime.now()` comparison; the remaining uses are timestamps and default factories.

Security note. Past-dated credentials now load, but are still excluded:
- `Credential.is_valid()` requires an unexpired, ACTIVE credential (`credential.py:157-160`).
- `OAuthIntegration.is_valid()` requires an unexpired token (`oauth_integration.py:203-207`), and `needs_refresh()` flags tokens near expiry.
- `Person.get_valid_credentials()` (`person.py:219-221`) and `get_valid_oauth_integrations()` (`person.py:249-251`) filter on those checks, and `person.py:564` collects integrations that need a refresh.

| #1496 Done-when item | Test (`tests/`) |
|---|---|
| Expiry fields accept past values on load | `test_1496_expiry_validators_reload.py` (4 fields); `test_1496_expiry_timezones.py::test_past_aware_value_reloads_and_reports_expired` (4 fields) |
| Timezone-aware and naive datetimes are normalised | `test_z_suffixed_value_compares_without_type_error`, `test_non_utc_offset_compares_the_instant` (+05:00 and -08:00), `test_naive_value_is_local_wall_clock_time` (4 fields each) |
| Dump a `Credential` and a `User` holding an `OAuthIntegration` expiring 1 s ahead, wait, reload, `is_expired()` True | `test_credential_and_user_reload_after_their_expiry_passes` |
| A `Z`-suffixed expiry validates without `TypeError` | `test_z_suffixed_value_compares_without_type_error` |
| Expired aware items are filtered, not crashed on | `test_person_filters_drop_expired_aware_items_without_crashing` |

Red/green:
- With the five comparison methods restored in memory to their `ad7613c8` naive versions, 30 of 42 fail: every `Z`, offset, aware-reload, future-valid and Person-filter case. The 12 that pass are the 8 naive cases (unchanged by design) and the 4 existing reload tests.
- At the tip, 46 of 46 pass. This includes two controls: `test_naive_expiry_keeps_its_v400_instant` shows a naive expiry keeps its instant and its v4.0.0 result and is stored naive, and `test_aware_value_is_stored_as_given` shows a `Z` value stays aware. The 1-second reload test is green at the tip. Its v4.0.0 failure is the future-only validator, observed in the falsification run above, and was not separately re-run.
- Config model, person, registry, Hydra and changelog suites: 2566 passed.

With every Done-when item mapped to a test, the PR now says `Fixes #1496`.

### Lifecycle and filter selection (loading is not authorization)

`tests/test_1496_expiry_lifecycle.py` uses a controlled clock: each model module's `utc_now` is patched, with no real sleep, network or secret. It covers:
- **Clock crossing:** a controlled clock crosses a previously future expiry WITHOUT changing the field. The object is dumped before the crossing and reloaded after it, then `is_expired`/`is_token_expired` and the `get_valid_*` selection are checked. The live object reports the crossing, as v4.0.0 could; unlike v4.0.0, the earlier dump still reloads.
- **Assignment validation (a separate test):** assigning a past `expires_at` is accepted and reports expired.
- **Loading:** a direct past load, and JSON and YAML round-trips.
- **Absent expiry:** valid with otherwise-valid fixtures. Controls show it does NOT validate a REVOKED credential, an inactive integration, a tokenless integration, or a non-active collaboration.
- **Exact boundary (`expires_at == now`):** the v4.0.0 operators are kept (`>` for `Credential`/`Collaborator`, `>=` for the OAuth token, `<` for `Collaboration.is_active`).
- **Equivalent aware instants:** `Z`, `+05:00` and `-08:00` for the same instant give the same answer.
- **Naive normalization:** naive values are local wall-clock time.

Labels: the `get_valid_*` tests prove FILTER SELECTION, not a refusal at secret-use time. No consumer gate exists (see the inventory: `from_account` enforcement is NONE). With `Credential.is_valid` and `OAuthIntegration.is_valid` stubbed to always `True` for a whole run, the 9 tests that assert `is_valid` or the filter selection fail and 47 pass. That shows only that these expectations depend on `is_valid`.

The ticket's 1-second reload test (`test_1496_expiry_timezones.py`) also uses the controlled clock now, not a real sleep.

Source inventory, in summary:
- The library's only path that uses a stored secret for these models is `GoogleWorkspaceClient.from_account` (`analytics/google_workspace.py:313-321`). It takes the integration from `Person.get_oauth_integration` (`person.py:242`, no filter) and passes `client_id`/`client_secret` to `from_oauth`, which starts a fresh OAuth flow when no valid token file exists.
- That path has no library-side validity or revocation gate. The gap is pre-existing: v4.0.0 had none either.
- Before this PR, a Person whose integration had a past `expires_at` could not be loaded, so the path was unreachable for it. Now it loads and runs a fresh OAuth flow, which is the refresh #1496 asks for. Token expiry is not the right gate there; `is_active` (deactivation) is. A follow-up issue is drafted but UNFILED: filing is currently blocked by a local guard.
- `Credential` secrets and OAuth access and refresh tokens have no use path in the library, so relaxing their validators changes load behaviour only.
- Provider-side rejection is not counted as library enforcement.

## Lead review

The change reverts additively. It is BREAKING, because past values no longer raise at construction (see CHANGELOG `[4.1.0]` BREAKING). Timezone handling changes no naive-value result. No claim in this artifact exceeds what was observed.
