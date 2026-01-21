"""
Management command to populate Census boundary crosswalk data.

Usage:
    python manage.py populate_crosswalks --source-year 2010 --target-year 2020 --type tract
    python manage.py populate_crosswalks --source-year 2010 --target-year 2020 --type tract --state 06
"""

from django.core.management.base import BaseCommand, CommandError

from siege_utilities.geo.django.services import CrosswalkPopulationService


class Command(BaseCommand):
    """Populate Census boundary crosswalk data."""

    help = "Populate Census boundary crosswalk data"

    GEOGRAPHY_TYPES = ["county", "tract", "blockgroup"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-year",
            type=int,
            required=True,
            help="Source (earlier) Census year (e.g., 2010)",
        )
        parser.add_argument(
            "--target-year",
            type=int,
            required=True,
            help="Target (later) Census year (e.g., 2020)",
        )
        parser.add_argument(
            "--type",
            type=str,
            required=True,
            choices=self.GEOGRAPHY_TYPES,
            help="Geography type",
        )
        parser.add_argument(
            "--state",
            type=str,
            help="State FIPS code or abbreviation (optional filter)",
        )
        parser.add_argument(
            "--weight-type",
            type=str,
            default="population",
            choices=["population", "housing", "area", "land_area"],
            help="Weight type (default: population)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing records instead of skipping",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Batch size for database operations",
        )

    def _normalize_state(self, state_input: str) -> str:
        """Convert state input to FIPS code."""
        if not state_input:
            return None

        if state_input.isdigit() and len(state_input) == 2:
            return state_input

        if state_input.isdigit() and len(state_input) == 1:
            return state_input.zfill(2)

        from siege_utilities.geo import normalize_state_identifier

        try:
            return normalize_state_identifier(state_input)
        except Exception:
            raise CommandError(
                f"Invalid state identifier: {state_input}. "
                "Use FIPS code (e.g., 06) or abbreviation (e.g., CA)"
            )

    def handle(self, *args, **options):
        source_year = options["source_year"]
        target_year = options["target_year"]
        geo_type = options["type"]
        state_input = options.get("state")
        weight_type = options.get("weight_type", "population")
        update_existing = options.get("update", False)
        batch_size = options.get("batch_size", 1000)

        if source_year >= target_year:
            raise CommandError("Source year must be earlier than target year")

        state_fips = self._normalize_state(state_input) if state_input else None

        service = CrosswalkPopulationService()

        self.stdout.write(
            f"Loading {geo_type} crosswalk from {source_year} to {target_year}..."
        )
        if state_fips:
            self.stdout.write(f"  Filtering to state {state_fips}")

        result = service.populate(
            geography_type=geo_type,
            source_year=source_year,
            target_year=target_year,
            state_fips=state_fips,
            weight_type=weight_type,
            update_existing=update_existing,
            batch_size=batch_size,
        )

        if result.success:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Crosswalk populated: {result.records_created} created, "
                    f"{result.records_updated} updated, "
                    f"{result.records_skipped} skipped"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Crosswalk population failed with {len(result.errors)} errors")
            )
            for error in result.errors[:10]:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
