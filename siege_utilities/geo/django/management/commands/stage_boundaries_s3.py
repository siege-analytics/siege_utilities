"""
Management command to stage TIGER boundaries on S3 for Spark broadcast joins.

Exports loaded boundary data to S3-compatible storage (MinIO/AWS) in
both Parquet (for Spark) and GeoJSON (for static map rendering) formats.

Layout:
    s3://{bucket}/boundaries/tiger/{type}/{year}/data.parquet
    s3://{bucket}/boundaries/tiger/{type}/{year}/data.geojson

Usage:
    python manage.py stage_boundaries_s3 --year 2020 --type county
    python manage.py stage_boundaries_s3 --year 2020 --type all --bucket boundaries
    python manage.py stage_boundaries_s3 --year 2020 --type tract --state 06
    python manage.py stage_boundaries_s3 --year 2020 --type county --format parquet
"""

import io
import json
import tempfile

from django.core.management.base import BaseCommand, CommandError

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None

try:
    import geopandas as gpd
    import pandas as pd
except ImportError:
    gpd = None
    pd = None

from siege_utilities.geo.django.models import (
    State, County, Tract, BlockGroup, Block, Place, ZCTA,
    CongressionalDistrict, StateLegislativeUpper, StateLegislativeLower,
    VTD,
)


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
            default="http://10.10.0.10:9000",
            help="S3 endpoint URL (default: MinIO at 10.10.0.10:9000)",
        )
        parser.add_argument(
            "--access-key",
            type=str,
            default="electinfo",
            help="S3 access key",
        )
        parser.add_argument(
            "--secret-key",
            type=str,
            default="electinfo123",
            help="S3 secret key",
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

        s3 = boto3.client(
            "s3",
            endpoint_url=options["endpoint_url"],
            aws_access_key_id=options["access_key"],
            aws_secret_access_key=options["secret_key"],
        )

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

        # Build GeoDataFrame from queryset
        gdf = self._queryset_to_gdf(qs, model)

        if output_format in ("parquet", "both"):
            self._upload_parquet(s3, bucket, prefix, gdf)

        if output_format in ("geojson", "both"):
            self._upload_geojson(s3, bucket, prefix, gdf)

    def _queryset_to_gdf(self, qs, model):
        """Convert a Django queryset with geometry to a GeoDataFrame."""
        from django.contrib.gis.geos import GEOSGeometry
        from shapely import wkt

        records = []
        for obj in qs.iterator(chunk_size=500):
            record = {
                "feature_id": obj.feature_id,
                "name": obj.name,
                "vintage_year": obj.vintage_year,
            }
            if hasattr(obj, "geoid"):
                record["geoid"] = obj.geoid
            if hasattr(obj, "state_fips"):
                record["state_fips"] = obj.state_fips
            if hasattr(obj, "geometry") and obj.geometry:
                record["geometry"] = wkt.loads(obj.geometry.wkt)
            else:
                record["geometry"] = None

            records.append(record)

        return gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")

    def _upload_parquet(self, s3, bucket, prefix, gdf):
        key = f"{prefix}/data.parquet"
        with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
            gdf.to_parquet(tmp.name, index=False)
            s3.upload_file(tmp.name, bucket, key)
        self.stdout.write(self.style.SUCCESS(f"    Uploaded s3://{bucket}/{key}"))

    def _upload_geojson(self, s3, bucket, prefix, gdf):
        key = f"{prefix}/data.geojson"
        geojson_str = gdf.to_json()
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=geojson_str.encode("utf-8"),
            ContentType="application/geo+json",
        )
        self.stdout.write(self.style.SUCCESS(f"    Uploaded s3://{bucket}/{key}"))
