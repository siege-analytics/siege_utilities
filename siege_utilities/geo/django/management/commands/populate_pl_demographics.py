"""
Management command to populate DemographicSnapshot from PL 94-171 data.

Usage:
    python manage.py populate_pl_demographics --state CA --year 2020
    python manage.py populate_pl_demographics --state CA --year 2020 --geography tract
    python manage.py populate_pl_demographics --state CA --year 2020 --tables P1 P2 H1
"""

import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """Populate DemographicSnapshot records from PL 94-171 redistricting files."""

    help = "Load PL 94-171 redistricting data into DemographicSnapshot"

    GEOGRAPHY_CHOICES = ["state", "county", "tract", "block_group", "block"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--state",
            type=str,
            required=True,
            help="State abbreviation, name, or FIPS code",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=2020,
            help="Census year (2010 or 2020, default: 2020)",
        )
        parser.add_argument(
            "--geography",
            type=str,
            default="tract",
            choices=self.GEOGRAPHY_CHOICES,
            help="Geography level (default: tract)",
        )
        parser.add_argument(
            "--tables",
            nargs="+",
            default=None,
            help="PL tables to load (e.g., P1 P2 H1). Default: all.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Bulk create batch size (default: 500)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing snapshots instead of skipping",
        )

    def handle(self, *args, **options):
        from django.contrib.contenttypes.models import ContentType

        from siege_utilities.config.census_constants import normalize_state_identifier
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader
        from siege_utilities.geo.django.models.demographics import DemographicSnapshot

        state = options["state"]
        year = options["year"]
        geography = options["geography"]
        tables = options["tables"]
        batch_size = options["batch_size"]
        update_existing = options["update"]

        # Validate state
        try:
            state_fips = normalize_state_identifier(state)
        except ValueError as e:
            raise CommandError(str(e))

        self.stdout.write(
            f"Loading PL 94-171 data: state={state_fips}, year={year}, "
            f"geography={geography}"
        )

        # Download and parse PL data
        downloader = PLFileDownloader()
        try:
            df = downloader.get_data(
                state=state_fips,
                year=year,
                geography=geography,
                tables=tables,
            )
        except Exception as e:
            raise CommandError(f"Failed to download PL data: {e}")

        if df.empty:
            self.stdout.write(self.style.WARNING("No data returned."))
            return

        self.stdout.write(f"Downloaded {len(df)} rows, {len(df.columns)} columns")

        # Resolve target model content type based on geography
        model = self._resolve_model(geography)
        if model is None:
            raise CommandError(f"No Django model for geography: {geography}")

        ct = ContentType.objects.get_for_model(model)

        # Find the GEOID column
        geoid_col = None
        for candidate in ["GEOID", "geoid", "GEOID20", "GEOID10"]:
            if candidate in df.columns:
                geoid_col = candidate
                break
        if geoid_col is None:
            raise CommandError(
                f"No GEOID column found in PL data. Columns: {list(df.columns)}"
            )

        # Identify variable columns (exclude metadata columns)
        metadata_cols = {
            geoid_col, "SUMLEV", "STATE", "COUNTY", "TRACT", "BLOCK",
            "BLKGRP", "NAME", "STUSAB", "LOGRECNO", "FILEID", "CHAESSION",
        }
        var_cols = [c for c in df.columns if c not in metadata_cols and c == c.upper()]

        created = 0
        updated = 0
        skipped = 0

        with transaction.atomic():
            to_create = []
            for _, row in df.iterrows():
                geoid = str(row[geoid_col])
                values = {}
                for col in var_cols:
                    val = row.get(col)
                    if val is not None and val != "" and str(val) != "nan":
                        try:
                            values[col] = float(val)
                        except (ValueError, TypeError):
                            pass

                if not values:
                    skipped += 1
                    continue

                existing = DemographicSnapshot.objects.filter(
                    content_type=ct,
                    object_id=geoid,
                    dataset="dec_pl",
                    year=year,
                ).first()

                if existing:
                    if update_existing:
                        existing.values.update(values)
                        existing.save()
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Set total_population from P1_001N if available
                    total_pop = values.get("P1_001N")
                    to_create.append(
                        DemographicSnapshot(
                            content_type=ct,
                            object_id=geoid,
                            dataset="dec_pl",
                            year=year,
                            values=values,
                            total_population=int(total_pop) if total_pop else None,
                        )
                    )

            if to_create:
                for i in range(0, len(to_create), batch_size):
                    batch = to_create[i : i + batch_size]
                    DemographicSnapshot.objects.bulk_create(
                        batch, ignore_conflicts=True
                    )
                created = len(to_create)

        self.stdout.write(
            f"Created={created}, updated={updated}, skipped={skipped}"
        )
        self.stdout.write(self.style.SUCCESS("Done."))

    def _resolve_model(self, geography_level: str):
        """Resolve geography level to Django model."""
        from django.apps import apps

        level_to_model = {
            "state": "State",
            "county": "County",
            "tract": "Tract",
            "block_group": "BlockGroup",
            "block": "Block",
        }
        model_name = level_to_model.get(geography_level)
        if model_name is None:
            return None
        try:
            return apps.get_model("siege_geo", model_name)
        except LookupError:
            return None
