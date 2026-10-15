"""
Management command to stage TIGER boundaries on S3 for Spark broadcast joins.

Exports loaded boundary data to S3-compatible storage (MinIO/AWS) in
both Parquet (for Spark) and GeoJSON (for static map rendering) formats.

Credentials use the standard boto3 provider chain, including AWS_ACCESS_KEY_ID,
AWS_SECRET_ACCESS_KEY and AWS_SESSION_TOKEN, shared profiles and IAM roles.
Set AWS_ENDPOINT_URL for S3-compatible storage, or override it with --endpoint-url.
Exports spool to temporary disk in batches of 500 rows before upload; allow
space for the complete output files in the system temporary directory.

Layout:
    s3://{bucket}/boundaries/tiger/{type}/{year}/data.parquet
    s3://{bucket}/boundaries/tiger/{type}/{year}/data.geojson

Usage:
    python manage.py stage_boundaries_s3 --year 2020 --type county
    python manage.py stage_boundaries_s3 --year 2020 --type all --bucket boundaries
    python manage.py stage_boundaries_s3 --year 2020 --type tract --state 06
    python manage.py stage_boundaries_s3 --year 2020 --type county --format parquet
"""

import json
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = type('ClientError', (Exception,), {})

try:
    import geopandas as gpd
except ImportError:
    gpd = None

from siege_utilities.geo.django.models import (
    State, County, Tract, BlockGroup, Block, Place, ZCTA,
    CongressionalDistrict, StateLegislativeUpper, StateLegislativeLower,
    VTD,
)

__all__ = ['Command']

EXPORT_CHUNK_SIZE = 500

GEOGRAPHY_MODEL_MAP = {
    "state": State,
    "county": County,
    "tract": Tract,
    "blockgroup": BlockGroup,
    "block": Block,
    "place": Place,
    "zcta": ZCTA,
    "cd": CongressionalDistrict,
    "sldu": StateLegislativeUpper,
    "sldl": StateLegislativeLower,
    "vtd": VTD,
}


class Command(BaseCommand):
    """Export TIGER boundaries to S3 in Parquet and/or GeoJSON format."""

    help = "Stage TIGER boundaries on S3 for Spark broadcast joins"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="Vintage year of boundaries to export",
        )
        parser.add_argument(
            "--type",
            type=str,
            required=True,
            choices=list(GEOGRAPHY_MODEL_MAP.keys()) + ["all"],
            help="Geography type to export",
        )
        parser.add_argument(
            "--state",
            type=str,
            default=None,
            help="State FIPS code filter (for tract, blockgroup, block)",
        )
        parser.add_argument(
            "--bucket",
            type=str,
            default="boundaries",
            help="S3 bucket name (default: boundaries)",
        )
        parser.add_argument(
            "--endpoint-url",
            type=str,
            default=None,
            help="Optional S3 endpoint override (otherwise AWS_ENDPOINT_URL or boto3 default)",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["parquet", "geojson", "both"],
            default="both",
            help="Output format (default: both)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be uploaded without actually uploading",
        )

    def handle(self, *args, **options):
        if boto3 is None:
            raise CommandError(
                "boto3 is required. Install with: pip install siege_utilities[s3]"
            )
        if gpd is None:
            raise CommandError(
                "geopandas is required. Install with: pip install siege_utilities[geo]"
            )

        year = options["year"]
        geo_type = options["type"]
        bucket = options["bucket"]
        output_format = options["format"]
        dry_run = options["dry_run"]

        # boto3's supported floor predates AWS_ENDPOINT_URL support. Resolve
        # configured endpoints here so an older SDK cannot silently send a
        # MinIO-targeted export to the default AWS S3 endpoint instead.
        endpoint_url = options["endpoint_url"]
        if endpoint_url is None and os.environ.get(
            "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", ""
        ).lower() != "true":
            endpoint_url = (
                os.environ.get("AWS_ENDPOINT_URL_S3")
                or os.environ.get("AWS_ENDPOINT_URL")
            )
        s3 = boto3.client("s3", endpoint_url=endpoint_url)

        # Ensure bucket exists
        if not dry_run:
            self._ensure_bucket(s3, bucket)

        types_to_export = (
            list(GEOGRAPHY_MODEL_MAP.keys()) if geo_type == "all"
            else [geo_type]
        )

        for gtype in types_to_export:
            self._export_type(
                s3, bucket, gtype, year,
                state_fips=options["state"],
                output_format=output_format,
                dry_run=dry_run,
            )

    def _ensure_bucket(self, s3, bucket: str):
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError:
            self.stdout.write(f"Creating bucket: {bucket}")
            s3.create_bucket(Bucket=bucket)

    def _export_type(self, s3, bucket, geo_type, year, state_fips=None,
                     output_format="both", dry_run=False):
        model = GEOGRAPHY_MODEL_MAP[geo_type]
        qs = model.objects.filter(vintage_year=year)

        if state_fips:
            qs = qs.filter(state_fips=state_fips)

        count = qs.count()
        if count == 0:
            self.stdout.write(
                self.style.WARNING(f"  {geo_type}/{year}: no records found, skipping")
            )
            return

        self.stdout.write(f"  {geo_type}/{year}: {count} records")

        prefix = f"boundaries/tiger/{geo_type}/{year}"
        if state_fips:
            prefix += f"/{state_fips}"

        if dry_run:
            if output_format in ("parquet", "both"):
                self.stdout.write(f"    [DRY RUN] Would upload s3://{bucket}/{prefix}/data.parquet")
            if output_format in ("geojson", "both"):
                self.stdout.write(f"    [DRY RUN] Would upload s3://{bucket}/{prefix}/data.geojson")
            return

        with tempfile.TemporaryDirectory(prefix="stage-boundaries-") as directory:
            parquet_path = (
                Path(directory) / "data.parquet"
                if output_format in ("parquet", "both") else None
            )
            geojson_path = (
                Path(directory) / "data.geojson"
                if output_format in ("geojson", "both") else None
            )
            self._write_exports(qs, parquet_path, geojson_path)
            for path in (parquet_path, geojson_path):
                if path is None:
                    continue
                key = f"{prefix}/{path.name}"
                extra_args = (
                    {"ContentType": "application/geo+json"}
                    if path == geojson_path else {}
                )
                s3.upload_file(str(path), bucket, key, ExtraArgs=extra_args)
                self.stdout.write(self.style.SUCCESS(f"    Uploaded s3://{bucket}/{key}"))

    def _iter_gdf_chunks(self, qs):
        """Yield EPSG:4326 frames without retaining the full queryset or export."""
        from shapely import wkt

        records = []
        offset = 0
        for obj in qs.iterator(chunk_size=EXPORT_CHUNK_SIZE):
            records.append({
                "feature_id": obj.feature_id,
                "name": obj.name,
                "vintage_year": obj.vintage_year,
                "geoid": obj.geoid,
                "state_fips": obj.state_fips,
                "geometry": wkt.loads(obj.geometry.wkt) if obj.geometry else None,
            })
            if len(records) == EXPORT_CHUNK_SIZE:
                yield gpd.GeoDataFrame(
                    records, geometry="geometry", crs="EPSG:4326",
                    index=range(offset, offset + len(records)),
                )
                offset += len(records)
                records = []

        if records:
            yield gpd.GeoDataFrame(
                records, geometry="geometry", crs="EPSG:4326",
                index=range(offset, offset + len(records)),
            )

    def _write_exports(self, qs, parquet_path, geojson_path):
        """Stream batches into one GeoParquet file and one GeoJSON collection."""
        if parquet_path is not None:
            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
            except ImportError as exc:
                raise CommandError(
                    "pyarrow is required for Parquet. "
                    "Install with: pip install siege_utilities[data]"
                ) from exc

            # Fixed model field types also handle an all-null geometry batch.
            schema = pa.schema([
                ("feature_id", pa.string()),
                ("name", pa.string()),
                ("vintage_year", pa.int64()),
                ("geoid", pa.string()),
                ("state_fips", pa.string()),
                ("geometry", pa.binary()),
            ])

        with ExitStack() as stack:
            geojson = None
            first_feature = True
            if geojson_path is not None:
                geojson = stack.enter_context(geojson_path.open("w", encoding="utf-8"))
                geojson.write('{"type": "FeatureCollection", "features": [')

            writer = None
            for gdf in self._iter_gdf_chunks(qs):
                if parquet_path is not None:
                    table = pa.Table.from_pandas(
                        gdf.to_wkb(), schema=schema, preserve_index=False,
                    )
                    if writer is None:
                        # A chunk's bbox/types cannot describe the entire file.
                        # GeoParquet permits omitted bbox and unknown types ([]).
                        metadata = {
                            "version": "1.0.0",
                            "primary_column": "geometry",
                            "columns": {"geometry": {
                                "encoding": "WKB",
                                "crs": gdf.crs.to_json_dict(),
                                "geometry_types": [],
                            }},
                        }
                        schema = table.schema.with_metadata({
                            **(table.schema.metadata or {}),
                            b"geo": json.dumps(metadata).encode("utf-8"),
                        })
                        parquet = stack.enter_context(parquet_path.open("wb"))
                        writer = stack.enter_context(pq.ParquetWriter(parquet, schema))
                    writer.write_table(table)

                if geojson is not None:
                    for feature in gdf.iterfeatures():
                        if not first_feature:
                            geojson.write(", ")
                        json.dump(feature, geojson)
                        first_feature = False

            if geojson is not None:
                geojson.write("]}")
