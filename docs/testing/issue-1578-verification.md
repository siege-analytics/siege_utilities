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
