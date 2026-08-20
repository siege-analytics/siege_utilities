# Parsons auth-bridge constructor-signature matrix

**Purpose:** verify that the 6 priority Parsons connectors accept credentials via constructor kwargs (not env-vars-only) so `siege_utilities/integrations/parsons/_auth.py` can bridge siege credential profiles → Parsons constructors without polluting the process environment.

**Closes P0-4 of parent epic:** [#1148 Epic: TMC Parsons integration](https://github.com/siege-analytics/siege_utilities/issues/1148).

## Priority connectors — constructor signatures

Six connectors chosen as Phase 2 / Phase 3 targets. Signatures read from `move-coop/parsons` `main` branch on 2026-08-19.

### VAN (also EveryAction)

Source: [`parsons/ngpvan/van.py`](https://github.com/move-coop/parsons/blob/main/parsons/ngpvan/van.py)

```python
class VAN(People, Events, Email, SavedLists, ...):
    def __init__(
        self,
        api_key: str | None = None,
        db: Literal["MyVoters", "MyCampaign", "MyMembers", "EveryAction"] | None = None,
    )
```

- **Kwargs accepted:** `api_key`, `db`.
- **Env fallback:** `VAN_API_KEY` (only if `api_key` is None).
- **EveryAction handling:** same `VAN` class; pass `db="EveryAction"`. No separate connector.
- **Construction side effects:** instantiates `VANConnector`, sets `page_size=200`. No network call at construction.

### ActionKit

Source: [`parsons/action_kit/action_kit.py`](https://github.com/move-coop/parsons/blob/main/parsons/action_kit/action_kit.py)

```python
class ActionKit:
    def __init__(self, domain=None, username=None, password=None):
```

- **Kwargs accepted:** `domain`, `username`, `password`.
- **Env fallback:** `ACTION_KIT_DOMAIN`, `ACTION_KIT_USERNAME`, `ACTION_KIT_PASSWORD` (via `check_env.check()`).
- **Construction side effects:** initializes `self.conn` = authenticated `requests.Session` (basic auth). No live network call, but session headers are baked at construction.

### Mobilize America

Source: [`parsons/mobilize_america/ma.py`](https://github.com/move-coop/parsons/blob/main/parsons/mobilize_america/ma.py)

```python
class MobilizeAmerica:
    def __init__(self, api_key=None):
```

- **Kwargs accepted:** `api_key`.
- **Env fallback:** `MOBILIZE_AMERICA_API_KEY`.
- **Construction side effects:** logs an info line if no key is available; does not raise. This means an accidentally-missing credential surfaces at first API call, not construction. Our wrapper must guard this and raise `ConnectorAuthError` at construction time when the profile is empty.

### ActBlue

Source: [`parsons/actblue/actblue.py`](https://github.com/move-coop/parsons/blob/main/parsons/actblue/actblue.py)

```python
class ActBlue:
    def __init__(
        self,
        actblue_client_uuid=None,
        actblue_client_secret=None,
        actblue_uri=None,
        max_retries=None,
    )
```

- **Kwargs accepted:** all four.
- **Env fallback:** `ACTBLUE_CLIENT_UUID` (required), `ACTBLUE_CLIENT_SECRET` (required), `ACTBLUE_URI` (default `https://secure.actblue.com/api/v1`), `ACTBLUE_MAX_RETRIES` (optional).
- **Construction side effects:** none documented beyond storing values.

### EveryAction

Same as VAN — pass `db="EveryAction"` to `parsons.VAN(...)`. There is no separate `EveryAction` class in Parsons. Our wrapper can expose `SiegeEveryAction` as a thin alias that instantiates `parsons.VAN(api_key=..., db="EveryAction")`.

### Redshift

Source: [`parsons/databases/redshift/redshift.py`](https://github.com/move-coop/parsons/blob/main/parsons/databases/redshift/redshift.py)

```python
class Redshift(RedshiftCreateTable, RedshiftCopyTable, RedshiftTableUtilities,
               RedshiftSchema, Alchemy, DatabaseConnector):
    def __init__(
        self,
        username=None,
        password=None,
        host=None,
        db=None,
        port=None,
        timeout=10,
        s3_temp_bucket=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        iam_role=None,
        use_env_token=True,
    )
```

- **Kwargs accepted:** all 11.
- **Env fallback:** `REDSHIFT_USERNAME`, `REDSHIFT_PASSWORD`, `REDSHIFT_HOST`, `REDSHIFT_DB`, `REDSHIFT_PORT`, `S3_TEMP_BUCKET`. AWS creds pulled via child classes from `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`.
- **Construction side effects:** none documented; connection lazy-instantiated.

## Summary table

| Connector | Kwarg auth? | Env fallback? | Construction I/O | Auth-error timing |
|---|---|---|---|---|
| VAN / EveryAction | ✅ | `VAN_API_KEY` | none | first API call |
| ActionKit | ✅ | `ACTION_KIT_{DOMAIN,USERNAME,PASSWORD}` | requests.Session init | first API call |
| Mobilize America | ✅ | `MOBILIZE_AMERICA_API_KEY` | INFO log if missing | first API call (silent construction) |
| ActBlue | ✅ | `ACTBLUE_{CLIENT_UUID,CLIENT_SECRET,URI,MAX_RETRIES}` | none | first API call |
| EveryAction | ✅ (via VAN) | `VAN_API_KEY` + `db="EveryAction"` | none | first API call |
| Redshift | ✅ | `REDSHIFT_*` + `AWS_*` | none | first `.execute()` |

**All 6 accept kwargs.** No connector is env-vars-only. This falsifies the "worst case" in the epic Fact Sheet §4 and confirms Phase 4 Tiger T2's mitigation shape: our `_auth.py` bridge never needs to set process-wide env vars.

## siege credential surface

Bridge target: [`siege_utilities/config/credential_manager.py`](../siege_utilities/config/credential_manager.py) `CredentialManager.get_credential(service, username, field, ...)`.

- Backend priority: `['files', 'env', '1password', 'keychain', 'prompt']`.
- Raises `CredentialNotFoundError` when no backend has the credential.
- Transport errors from per-backend helpers propagate (SU-1 compliant).

The bridge can compose `get_credential(service, username, field)` calls into the connector-specific kwarg map.

## Design: `siege_utilities/integrations/parsons/_auth.py`

### Bridge function

```python
def bridge_credentials(
    connector: str,
    profile: str | None = None,
    *,
    manager: CredentialManager | None = None,
) -> dict[str, Any]:
    """Resolve siege profile → Parsons connector constructor kwargs.

    Args:
        connector: One of {"van", "everyaction", "action_kit", "mobilize_america",
            "actblue", "redshift"}. Determines which kwargs are returned.
        profile: Named profile in siege's credential surface (e.g., "acme-van").
            If None, uses the default siege profile.
        manager: Injectable CredentialManager for testing.

    Returns:
        dict of kwargs suitable for splatting into the corresponding Parsons
        connector constructor (e.g., ``parsons.VAN(**bridge_credentials("van"))``).

    Raises:
        ConnectorAuthError: if any required credential for `connector` is missing.
            Never returns a partial dict; never sets process env vars.
        ConnectorError: for unknown `connector` names (SU-1: no silent None-return).
    """
```

### Per-connector kwarg maps

Each connector name in the bridge maps to a fixed list of `(kwarg_name, siege_service, siege_field)` triples:

| Connector | Kwargs → siege lookup |
|---|---|
| `van` | `api_key` → `get_credential("van", profile, "api_key")` + optional `db` |
| `everyaction` | `api_key` → `get_credential("van", profile, "api_key")`, hardcode `db="EveryAction"` |
| `action_kit` | `domain` / `username` / `password` → three `get_credential("actionkit", ...)` calls |
| `mobilize_america` | `api_key` → `get_credential("mobilize", profile, "api_key")` |
| `actblue` | `actblue_client_uuid` / `actblue_client_secret` → two `get_credential("actblue", ...)` calls |
| `redshift` | full 11-kwarg map — depends on RS profile schema which needs a separate design pass in P1-4 |

### Error semantics

- Missing credential in siege profile → `ConnectorAuthError` (raised, not None-returned per SU-1).
- Unknown connector name → `ConnectorError`.
- Multiple missing kwargs → raise on the FIRST missing, name it in the exception message; don't try to fail-with-partial-diagnostic (that pattern hides the primary error).

### env-var fallback opt-in (not needed for MVP)

Fact Sheet §4 asked whether we need an `allow_env_var_setting=True` escape hatch. **Answer: no**, because all 6 priority connectors accept kwargs. The escape hatch would only be needed if a future connector was env-vars-only; we can add it in P1-4 as a follow-up if a Phase 3 connector requires it. Defer.

## Falsification

Per epic Fact Sheet §4, this doc's central claim is:

> All 6 priority connectors accept credentials via constructor kwargs (no env-vars-only connector).

**Verified against source** for all 6. Falsifies if a future Parsons release changes any of the 6 constructor signatures to remove the credential kwargs (breaking change on Parsons's side).

Additional falsification: if any of the 6 constructors performs a network call at construction time that our wrapper's error mapping does not catch, `_auth.py`'s bridge is incomplete. Empirical check: run `parsons.VAN(api_key="INVALID")` in a no-network sandbox and confirm construction succeeds; the test lives in P1-4's test suite.

## Blocks

- P1-4 (`_auth.py` implementation). Bridge design in this doc is the input.

## References

- Parsons docs: <https://move-coop.github.io/parsons/html/stable/>
- siege credential manager: [`../siege_utilities/config/credential_manager.py`](../siege_utilities/config/credential_manager.py)
- Parent epic: [#1148](https://github.com/siege-analytics/siege_utilities/issues/1148)
- This ticket: [#1152](https://github.com/siege-analytics/siege_utilities/issues/1152)
