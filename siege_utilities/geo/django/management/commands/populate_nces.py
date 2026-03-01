"""
Management command for populating NCES education data.

Usage:
    python manage.py populate_nces --year 2023 --action locale_boundaries
    python manage.py populate_nces --year 2023 --action school_locations --state 06
    python manage.py populate_nces --year 2023 --action enrich_districts
    python manage.py populate_nces --year 2023 --action all
"""

from django.core.management.base import BaseCommand, CommandError


VALID_ACTIONS = ["locale_boundaries", "school_locations", "enrich_districts", "all"]


class Command(BaseCommand):
    help = "Populate NCES education data (locale boundaries, school locations, district enrichment)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="NCES publication year (e.g. 2023)",
        )
        parser.add_argument(
            "--action",
            type=str,
            required=True,
            choices=VALID_ACTIONS,
            help="Action to perform",
        )
        parser.add_argument(
            "--state",
            type=str,
            default=None,
            help="State FIPS code or abbreviation (for school_locations)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            default=False,
            help="Update existing records instead of skipping",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of records per database batch (default: 500)",
        )
        parser.add_argument(
            "--cache-dir",
            type=str,
            default=None,
            help="Directory for caching downloaded NCES files",
        )

    def handle(self, *args, **options):
        from siege_utilities.geo.django.services.nces_service import (
            NCESPopulationService,
        )

        year = options["year"]
        action = options["action"]
        state = options.get("state")
        update = options["update"]
        batch_size = options["batch_size"]
        cache_dir = options.get("cache_dir")

        service = NCESPopulationService(cache_dir=cache_dir)

        actions = (
            ["locale_boundaries", "school_locations", "enrich_districts"]
            if action == "all"
            else [action]
        )

        for act in actions:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Running: {act} for year {year}")
            self.stdout.write(f"{'='*60}")

            if act == "locale_boundaries":
                result = service.populate_locale_boundaries(
                    year=year,
                    update_existing=update,
                    batch_size=batch_size,
                )
            elif act == "school_locations":
                result = service.populate_school_locations(
                    year=year,
                    state_fips=state,
                    update_existing=update,
                    batch_size=batch_size,
                )
            elif act == "enrich_districts":
                result = service.enrich_school_districts(
                    year=year,
                    update_existing=update,
                )
            else:
                raise CommandError(f"Unknown action: {act}")

            # Report results
            self.stdout.write(
                f"  Created: {result.records_created}\n"
                f"  Updated: {result.records_updated}\n"
                f"  Skipped: {result.records_skipped}\n"
                f"  Total:   {result.total_processed}"
            )

            if result.errors:
                self.stderr.write(
                    self.style.ERROR(f"  Errors ({len(result.errors)}):")
                )
                for err in result.errors[:10]:
                    self.stderr.write(f"    - {err}")
                if len(result.errors) > 10:
                    self.stderr.write(f"    ... and {len(result.errors) - 10} more")
            else:
                self.stdout.write(self.style.SUCCESS("  Status: OK"))
