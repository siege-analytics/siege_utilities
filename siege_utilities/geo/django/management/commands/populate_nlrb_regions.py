"""
Management command to populate NLRB region data.

Usage:
    python manage.py populate_nlrb_regions
    python manage.py populate_nlrb_regions --year 2024
    python manage.py populate_nlrb_regions --year 2024 --update
    python manage.py populate_nlrb_regions --dissolve-counties
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Populate NLRB region boundaries from built-in registry."""

    help = "Populate NLRB region data from built-in region registry"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=2024,
            help="Vintage year for the region records (default: 2024)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing records instead of skipping",
        )
        parser.add_argument(
            "--dissolve-counties",
            action="store_true",
            help="Build region geometry by dissolving county boundaries",
        )

    def handle(self, *args, **options):
        from siege_utilities.geo.django.services.nlrb_service import (
            NLRBPopulationService,
        )

        service = NLRBPopulationService()
        result = service.populate(
            vintage_year=options["year"],
            update_existing=options["update"],
            dissolve_counties=options["dissolve_counties"],
        )

        self.stdout.write(
            f"NLRB regions: created={result.records_created}, "
            f"updated={result.records_updated}, "
            f"skipped={result.records_skipped}"
        )

        if result.errors:
            for err in result.errors:
                self.stderr.write(self.style.ERROR(err))
        else:
            self.stdout.write(self.style.SUCCESS("Done."))
