"""
Management command to populate NLRB region data.

Usage:
    python manage.py populate_nlrb_regions
    python manage.py populate_nlrb_regions --year 2024
    python manage.py populate_nlrb_regions --year 2024 --update
    python manage.py populate_nlrb_regions --dissolve-counties
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

__all__ = ['Command']


class Command(BaseCommand):
    """Populate NLRB region boundaries from built-in registry."""

    help = "Populate NLRB region data from built-in region registry"

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-partial",
            action="store_true",
            help="Allow reported errors if at least one record was created or updated",
        )
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
        from siege_utilities.geo.django.models import NLRBRegion
        from siege_utilities.geo.django.services.nlrb_service import (
            NLRBPopulationService,
        )
        from siege_utilities.geo.providers.nlrb_regions import NLRB_REGIONS

        # Report across all vintages; removed registry keys require manual cleanup.
        stale_regions = list(
            NLRBRegion.objects.exclude(region_number__in=NLRB_REGIONS)
            .values("region_number")
            .annotate(row_count=Count("pk"))
            .order_by("region_number")
        )
        self.stdout.write(
            f"NLRB registry: stale_registry_rows={sum(row['row_count'] for row in stale_regions)}, "
            f"region_numbers={[row['region_number'] for row in stale_regions]} "
            "(all vintages; report only, no rows deleted)"
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
            f"skipped={result.records_skipped}, "
            f"without_geometry={result.records_without_geometry}"
        )

        if result.records_without_geometry:
            self.stdout.write(self.style.WARNING(
                f"Incomplete geometry: {result.records_without_geometry} regions "
                "have no geometry (registry-only or empty/partial county coverage)."
            ))

        if result.errors:
            for err in result.errors:
                self.stderr.write(self.style.ERROR(err))
            if (
                not options.get("allow_partial", False)
                or result.records_created + result.records_updated == 0
            ):
                raise CommandError(
                    f"NLRB region population failed with {len(result.errors)} errors"
                )
        elif not result.records_without_geometry:
            self.stdout.write(self.style.SUCCESS("Done."))
