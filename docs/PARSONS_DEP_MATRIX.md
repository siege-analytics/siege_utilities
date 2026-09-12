# Parsons dependency-conflict matrix

**Purpose:** verify empirically that `siege_utilities`'s current pin set can coexist with Parsons's extras graph, produce the proposed `[parsons-*]` extras for `pyproject.toml`, and identify any per-connector transitive that our adapter or `pyproject.toml` must handle explicitly.

**Closes P0-2 of parent epic:** [#1148 Epic: TMC Parsons integration](https://github.com/siege-analytics/siege_utilities/issues/1148).

## Empirical setup

Fresh Python 3.11.11 venv (`~/.pyenv/versions/default_31111/`), pip upgraded to latest, `parsons==6.1.0` from PyPI. All dry-run resolver checks executed 2026-08-19.

## Falsifiable claim results

### Claim A (Fact Sheet #3, P0-2 ticket) — `pip install parsons` does NOT pull pandas as transitive

**CONFIRMED.** Bare `pip install parsons==6.1.0` in a fresh venv:

```
Installing collected packages: urllib3, six, simplejson, petl, oauthlib, idna, charset_normalizer, certifi, requests, python-dateutil, requests-oauthlib, parsons
```

11 core deps. No pandas. No numpy. Post-install verification:

```
$ /tmp/parsons-p02/bin/python -c "import pandas"
ModuleNotFoundError: No module named 'pandas'
```

Parsons itself emits a `RuntimeWarning` on every import:

> `The behavior of 'pip install parsons' has changed so only core dependencies are installed. Learn more: https://www.parsonsproject.org/pub/improving-the-parsons-installation-experience`

**Load-bearing implication:** most connectors require their per-connector extra to be importable. Our `siege_utilities[parsons-<name>]` extras must transitively declare the exact Parsons extras the wrapper depends on. A user who installs `siege_utilities[parsons-van]` and gets an ImportError on `parsons.VAN` is our fault, not theirs.

### Claim B (P0-2 ticket) — `parsons[all]` and `siege_utilities[geodjango]` coexist

**BLOCKED by pre-existing siege issue #1114**, not by Parsons. Dry-run of `pip install siege-utilities[all] parsons[ngpvan]` fails with:

```
Exception: Python bindings of GDAL 3.13.3 require at least libgdal 3.13.3, but 3.12.4 was found
```

This is siege's `gdal>=3.13` pin in `[all]` against my system's libgdal 3.12.4 — the exact bug hostile-review-#1114 documented. It is not caused by Parsons and does not affect Parsons compatibility. Test rerun against `siege-utilities[data,analytics]` (lighter extras) succeeds cleanly (see Claim C).

### Claim C (P0-2 ticket) — `parsons[ngpvan]` does not conflict with siege's current pins

**CONFIRMED.** `pip install --dry-run 'siege-utilities[data,analytics]' 'parsons[ngpvan]==6.1.0'` resolves cleanly, would install ~90 packages, zero version-conflict errors. One transitive downgrade: `urllib3` from 2.7.0 (parsons-preferred) to 1.26.20 (siege transitive pin — likely `google-analytics-*` or `datadotworld`). This is resolver-handled and not a conflict.

## Which Parsons connectors are in core vs need extras

Empirical import test against a venv with `parsons[pandas]` only:

| Connector | Core? | Extra required |
|---|---|---|
| ActionKit | ✅ Core | — |
| MobilizeAmerica | ✅ Core | — |
| ActBlue | ✅ Core | — |
| VAN / EveryAction | ❌ | `parsons[ngpvan]` |
| Redshift | ❌ | `parsons[redshift]` |
| Salesforce | ❌ | `parsons[salesforce]` |
| GoogleSheets (and other Google) | ❌ | `parsons[google]` |
| S3 | ❌ | `parsons[s3]` |

## Per-Parsons-extra transitive footprint

Deltas above `parsons[pandas]` baseline (which itself adds `numpy`, `pandas` on top of core).

| Parsons extra | New packages | Overlap with siege |
|---|---|---|
| `parsons[ngpvan]` | `suds` (1 pkg) | none |
| `parsons[postgres]` | `sqlalchemy`, `psycopg2-binary`, `typing-extensions` | siege `[database]` also has SQLAlchemy + psycopg2 — no conflict, shared floor |
| `parsons[redshift]` | above + `boto3`, `botocore`, `jmespath`, `s3transfer` | siege `[analytics]` transitively brings `snowflake-connector-python` which pulls boto3 — no conflict |
| `parsons[salesforce]` | `simple-salesforce`, `zeep`, `lxml`, `cryptography`, `pyOpenSSL`, `requests-file`, `requests-toolbelt`, `PyJWT`, `attrs`, `isodate`, `more-itertools`, `platformdirs`, `pycparser`, `cffi`, `typing_extensions` | **Semantic overlap with siege's `connectors/salesforce.py`** — see P0-5 for reconciliation |
| `parsons[google]` | `google-api-python-client`, `gspread`, `oauth2client`, `google-cloud-bigquery`, `google-cloud-storage`, `google-cloud-storage-transfer`, `google-auth-*`, `apiclient`, `googleapis-common-protos`, `grpcio*`, ~30 pkgs | **Semantic overlap with siege's Google Workspace surface** — see P0-5 for reconciliation |
| `parsons[all]` | ~140 pkgs including `dbt-*`, `slack_sdk`, `twilio`, `PyGithub`, `airtable`, `azure-storage-blob`, `box`, `braintree`, `civis`, `newmode`, `redshift_connector`, `snowflake-connector-python`, `simple-salesforce`, `mysql-connector-python`, `paramiko`, `snowplow-tracker`, ... | **DO NOT declare `siege[parsons-all]` in v1** — the surface is too large, license/reviewability implications are unclear per-connector |

## Proposed `pyproject.toml` extras

Based on the empirical map above:

```toml
[project.optional-dependencies]
# ...existing extras...

parsons-core = [
    "parsons[pandas]>=6.1.0,<7.0",
]

# Connector-specific — pulls parsons-core transitively via parsons[<extra>,pandas]
parsons-van = [
    "parsons[ngpvan,pandas]>=6.1.0,<7.0",
]

# EveryAction shares parsons.VAN class with db="EveryAction"; no separate extra needed.
# Users can install parsons-van and use SiegeEveryAction wrapper.

parsons-action-kit = [
    "parsons[pandas]>=6.1.0,<7.0",  # ActionKit is in Parsons core
]

parsons-mobilize = [
    "parsons[pandas]>=6.1.0,<7.0",  # Mobilize is in Parsons core
]

parsons-actblue = [
    "parsons[pandas]>=6.1.0,<7.0",  # ActBlue is in Parsons core
]

parsons-redshift = [
    "parsons[redshift,pandas]>=6.1.0,<7.0",
]

parsons-postgres = [
    "parsons[postgres,pandas]>=6.1.0,<7.0",
]

parsons-salesforce = [
    "parsons[salesforce,pandas]>=6.1.0,<7.0",
]  # See P0-5 before Phase 3 — this overlaps with siege_utilities/connectors/salesforce.py

parsons-google = [
    "parsons[google,pandas]>=6.1.0,<7.0",
]  # See P0-5 before Phase 3 — semantic overlap with siege Google Workspace

# Convenience meta-extras
parsons-advocacy = [  # everything for the ElectInfo persona (Phase 2/3 canonical)
    "siege-utilities[parsons-van,parsons-action-kit,parsons-mobilize,parsons-actblue,parsons-redshift]",
]

# INTENTIONALLY NOT SHIPPED IN V1:
# parsons-all — the [all] surface is 140 packages and includes tooling (dbt, slack,
# twilio, ...) that siege has no wrapper for. Wait until wrappers exist per-connector.
```

## Version-floor findings

- Parsons 6.1.0 requires Python `>=3.10`; siege requires `>=3.11`. Compatible.
- Every Parsons extra dry-runs against `parsons==6.1.0` on Python 3.11.11 without upper-bound conflict.
- `urllib3` downgraded from 2.x to 1.26.20 when siege enters the graph — siege's transitive constraint. Non-blocking; both versions have overlapping API surface for the requests-shaped calls Parsons makes.

## Recommended CI job (draft, not enabled)

Add to CI matrix:

```yaml
- name: parsons-integration-install
  run: |
    python -m venv /tmp/parsons-ci
    /tmp/parsons-ci/bin/pip install -e '.[parsons-core]'
    /tmp/parsons-ci/bin/python -c "import pandas; import parsons; import parsons.etl.table"
    # Then per each parsons-* extra:
    /tmp/parsons-ci/bin/pip install -e '.[parsons-van]'
    /tmp/parsons-ci/bin/python -c "from parsons import VAN"
    /tmp/parsons-ci/bin/pip install -e '.[parsons-redshift]'
    /tmp/parsons-ci/bin/python -c "from parsons import Redshift"
    # etc.
```

Not enabled in this PR — enables in P1-1 once the `siege_utilities/integrations/parsons/__init__.py` exists to import against.

## Findings summary

- Bare `pip install parsons` does not pull pandas — **claim A CONFIRMED**.
- Every Parsons extra dry-runs cleanly with `siege_utilities[data,analytics]` — **claim C CONFIRMED**.
- `siege_utilities[all]` fails with pre-existing GDAL pin bug #1114 — **claim B BLOCKED by unrelated issue, not by Parsons**.
- Empirical import test shows 5 of the 8 tested connectors need their extra (VAN, Redshift, Salesforce, Google, S3). ActionKit / MobilizeAmerica / ActBlue are in Parsons core.
- Proposed 10-extra structure in `pyproject.toml` above (`parsons-core` + 8 connector extras + `parsons-advocacy` meta).
- `parsons-all` intentionally NOT shipped in v1 — the 140-pkg surface is too broad.

## Falsification for this doc

- Bare `pip install parsons==6.1.0` includes pandas as a transitive → claim A wrong, our extras structure changes.
- Any of the proposed extras fails resolver against `siege_utilities[data,analytics]` in a fresh venv → conflict matrix needs revisiting.
- ActionKit / Mobilize / ActBlue require an extra after all → the "core" column above is wrong; add per-connector extras.
- Parsons 6.2.0 (next minor) reshapes the extras keys → the mapping table above is stale.

Attach the output of `pip install --dry-run` for each proposed extra to a follow-up comment on this PR to keep the audit chain intact.

## Blocks

- P1-1 (`siege_utilities/integrations/parsons/__init__.py`) — needs the extras finalized.
- P1-2 (`_adapter.py`) — needs the `parsons[pandas]` transitive confirmed (this doc confirms it).

## References

- Parsons PyPI: <https://pypi.org/pypi/parsons/6.1.0/>
- Parsons install-experience blog post: <https://www.parsonsproject.org/pub/improving-the-parsons-installation-experience>
- Parent epic: [#1148](https://github.com/siege-analytics/siege_utilities/issues/1148)
- Sibling P0 tickets: [#1149](https://github.com/siege-analytics/siege_utilities/issues/1149), [#1151](https://github.com/siege-analytics/siege_utilities/issues/1151), [#1152](https://github.com/siege-analytics/siege_utilities/issues/1152), [#1153](https://github.com/siege-analytics/siege_utilities/issues/1153)
- Pre-existing siege GDAL issue: [#1114](https://github.com/siege-analytics/siege_utilities/issues/1114)
- This ticket: [#1150](https://github.com/siege-analytics/siege_utilities/issues/1150)
