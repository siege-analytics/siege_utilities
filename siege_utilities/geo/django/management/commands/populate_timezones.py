"""
Management command to populate timezone boundary data.

Usage:
    python manage.py populate_timezones --file /path/to/timezones.geojson
    python manage.py populate_timezones --file /path/to/timezones.geojson.zip --year 2024
    python manage.py populate_timezones --file timezones.geojson --update
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Populate timezone boundary data from timezone-boundary-builder GeoJSON."""

    help = "Load timezone boundaries from timezone-boundary-builder GeoJSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Path to GeoJSON or .zip file from timezone-boundary-builder",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=2024,
            help="Vintage year for the records (default: 2024)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing records instead of skipping",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Bulk create batch size (default: 100)",
        )

    def handle(self, *args, **options):
        from siege_utilities.geo.django.services.timezone_service import (
            TimezonePopulationService,
        )

        service = TimezonePopulationService()
        result = service.populate_from_geojson(
            geojson_path=options["file"],
            vintage_year=options["year"],
            update_existing=options["update"],
            batch_size=options["batch_size"],
        )

        self.stdout.write(
            f"Timezones: created={result.records_created}, "
            f"updated={result.records_updated}, "
            f"skipped={result.records_skipped}"
        )

        if result.errors:
            for err in result.errors:
                self.stderr.write(self.style.ERROR(err))
        else:
            self.stdout.write(self.style.SUCCESS("Done."))
