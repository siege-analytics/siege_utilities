# Issue #1578 verification

The command at the starting commit dd8864c2 was identical to its v4.0.0
version (`git diff --exit-code v4.0.0 -- <command>` passed). Inspection
confirmed that argparse defaults reached `boto3.client` directly. The
existing Django `iterator(chunk_size=500)` still fed one unbounded record
list, one GeoDataFrame, and one complete GeoJSON string.

Credentials now resolve through boto3's standard provider chain, including
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, shared profiles,
and roles. Both --secret-key and --access-key are removed. --endpoint-url
is an optional override with default None. The command explicitly forwards
AWS_ENDPOINT_URL_S3 (service-specific) ahead of AWS_ENDPOINT_URL to cover the
supported boto3 floor (>=1.28.0), which predates endpoint environment support.
AWS_IGNORE_CONFIGURED_ENDPOINT_URLS=true disables both environment endpoints
but not an explicit --endpoint-url override; without configured endpoints,
boto3 selects its normal AWS endpoint. Credentials still use boto3's chain.

The export consumes 500-row GeoDataFrames and writes Parquet row groups and
GeoJSON features to temporary files. Both files finish before upload.
The original S3 keys, optional state path, columns, EPSG:4326 CRS, GeoJSON
feature IDs, and GeoJSON content type are preserved. Temporary disk must
hold the complete selected outputs. GeoParquet uses WKB and omits optional
whole-file bounds instead of publishing a first-batch bounding box. Its
unknown geometry-types array follows the
[GeoParquet 1.0 specification](https://geoparquet.org/releases/v1.0.0/).

## Test evidence

Interpreter: /Users/dheerajchand/.pyenv/versions/default_31111/bin/python

```text
python -m pytest tests/test_stage_boundaries_s3.py tests/test_stage_boundaries_s3_errors.py --no-cov -q
Fixed implementation: 22 passed
v4.0.0 implementation: 15 failed, 7 passed
Restored implementation: 22 passed
```

A separate baseline run isolated the core regressions from ancillary
Parquet/error-path checks:

```text
python -m pytest tests/test_stage_boundaries_s3.py --no-cov -q --tb=no \
  -k 'no_flags or endpoint_default or credential_flags or environment_chain or shared_profile or default_aws_endpoint or serializes_before'
v4.0.0: 11 failed (trimmed)
```

The supported boto3 floor exposed an additional endpoint regression: before
explicit forwarding, a client shim that models an older boto3 received
`endpoint_url=None` despite `AWS_ENDPOINT_URL` / `AWS_ENDPOINT_URL_S3`
being set (2 failures, 2 other precedence cases passed). After repair, all
four precedence cases pass; the exact rebased-tree S3 test module passes
25 cases under the GDAL-equipped interpreter. These test client-call args
without contacting S3 and preserve the existing real boto3 session tests.

The core test names are:

- test_no_flags_have_no_credential_defaults
- test_endpoint_default_is_none
- test_credential_flags_are_rejected (both removed flags)
- test_handle_uses_boto3_environment_chain (environment and CLI endpoint)
- test_handle_uses_shared_profile_credentials
- test_handle_uses_default_aws_endpoint
- test_export_serializes_before_consuming_next_batch (all three formats)

The bounded-consumption test refuses to yield the next batch until the
first has been serialized. Output tests read real Parquet and GeoJSON,
including a null-geometry first batch and a partial final batch. Error
checks directly trigger optional import handlers, missing dependencies,
database interruption, upload credential
failure, and bucket-creation denial. AWS sessions are real but isolated;
no live S3 service or database is contacted.

## Caller and notebook audit

Repository searches found no callers passing either removed credential
flag and no external uses of the replaced private export helpers. External
scheduler scripts are unknown; any passing these flags must migrate to
environment variables or a credential provider. The no-flags parser test
relaxes only the unrelated required year/type inputs before parsing [].

| Public surface | Contract change | Notebooks affected | Notebook coverage |
| --- | --- | --- | --- |
| stage_boundaries_s3 arguments | Remove credential flags; endpoint defaults to None | None | Existing documentation gap |

The local interpreter emitted a pre-existing Requests dependency warning.
The old implementation's path-based Parquet calls also hit a native Arrow
filesystem-registration error here. The 11 isolated regression failures
exercise credentials and streaming directly, independently of that error.
The fixed implementation writes through explicit local file handles and
passes the Parquet round-trip checks.

Credential ROTATION is required on every system where the exposed secret
is or was valid. Rotation is an operator action outside this repository.
No credential rotation, git-history purge, or wheel removal was attempted.

## Forward fix after PR #1646

Against develop b2bc5435, the removed credential options now remain hidden
from help and raise CommandError during parsing. Both `--flag value` and
`--flag=value` are rejected without including the value in the error:

```text
--access-key was removed; set AWS_ACCESS_KEY_ID or use a boto3 profile
--secret-key was removed; set AWS_SECRET_ACCESS_KEY or use a boto3 profile
```

`tests/test_management_command_parsers.py` discovers every public command
module under `siege_utilities/**/management/commands/`, imports its Command,
and builds its real Django parser. It also inspects subparsers. Any option
whose destination matches `key|secret|token|password|endpoint` must default
to None; failures report only destination names, never default values.
The normal CI `test` job collects these unit tests on Python 3.11-3.14.
They use no database or network and have no `postgis` or `integration` marker.
Django and GDAL are needed to import the real command modules; minimal
environments skip with installation guidance, while the full matrix
installs those dependencies.

The guard currently covers classify_urbanicity, populate_boundaries,
populate_congressional_terms, populate_crosswalks, populate_demographics,
populate_nces, populate_nlrb_regions, populate_pl_demographics,
populate_timezones, and stage_boundaries_s3. New command files are discovered
automatically.

Using the interpreter named above, the forward-fix checks produced:

```text
python -m pytest tests/test_management_command_parsers.py --no-cov -q
Unmodified develop command: 4 failed, 11 passed
Fixed command: 15 passed

Revert only stage_boundaries_s3.py to develop b2bc5435:
  -k reject_without_echoing: 4 failed, 11 deselected
  Each failure is the sentinel-absent assertion, covering both flags/forms.

Inject parser.add_argument("--secret-key", default="<dummy>") into
populate_timezones.add_arguments:
  -k sensitive_defaults: 1 failed, 9 passed, 5 deselected
  Failure identifies populate_timezones and secret_key without the dummy value.

Restore both scratch changes:
python -m pytest tests/test_management_command_parsers.py \
  tests/test_stage_boundaries_s3.py tests/test_stage_boundaries_s3_errors.py --no-cov -q
39 passed, 0 skipped
```

The four rejection cases assert both sentinel absence and the complete
remediation message. The prior two rejection cases were moved and expanded
from the export module into the parser module so they do not require boto3,
GeoPandas, or PyArrow to run. A separate case checks that help hides both
removed options. The existing no-credential-default, boto3 provider-chain,
endpoint, and bounded-export tests remain green.

No model changed. `makemigrations siege_geo --check --dry-run` reports no
changes. No notebook calls this command; its existing documentation gap
remains, with no notebook call sites requiring an update.
