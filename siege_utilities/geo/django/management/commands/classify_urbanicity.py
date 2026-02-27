"""
Management command to classify tract urbanicity from Census data.

Usage:
    python manage.py classify_urbanicity --year 2020
    python manage.py classify_urbanicity --year 2020 --state CA
    python manage.py classify_urbanicity --year 2020 --state 06 --overwrite
    python manage.py classify_urbanicity --year 2020 --urban-area-year 2020
"""

from django.core.management.base import BaseCommand, CommandError

from siege_utilities.geo.django.services.urbanicity_service import (
    UrbanicityClassificationService,
)


class Command(BaseCommand):
    """Classify Census tracts into NCES locale codes using population and distance to urban areas."""

    help = (
        "Classify Census tract urbanicity (NCES locale codes 11-43) "
        "using tract population and distance to nearest Census Urban Area."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="Census vintage year for tracts and demographics",
        )
        parser.add_argument(
            "--state",
            type=str,
            help="State FIPS code or abbreviation (optional; classifies all states if omitted)",
        )
        parser.add_argument(
            "--urban-area-year",
            type=int,
            help="Vintage year for UrbanArea boundaries (defaults to --year)",
        )
        parser.add_argument(
            "--dataset",
            type=str,
            default="acs5",
            help="Census dataset for population lookup (default: acs5)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Reclassify tracts that already have an urbanicity code",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for database updates (default: 500)",
        )

    def _normalize_state(self, state_input: str) -> str:
        """Convert state input to 2-digit FIPS code."""
        if state_input.isdigit() and len(state_input) <= 2:
            return state_input.zfill(2)

        from siege_utilities.config.census_constants import normalize_state_identifier

        try:
            return normalize_state_identifier(state_input)
        except ValueError:
            raise CommandError(
                f"Invalid state identifier: {state_input}. "
                "Use FIPS code (e.g., 06) or abbreviation (e.g., CA)"
            )

    def handle(self, *args, **options):
        year = options["year"]
        state_input = options.get("state")
        urban_area_year = options.get("urban_area_year")
        dataset = options["dataset"]
        overwrite = options.get("overwrite", False)
        batch_size = options.get("batch_size", 500)

        state_fips = self._normalize_state(state_input) if state_input else None

        self.stdout.write(
            f"Classifying tract urbanicity for year {year}"
            + (f", state {state_fips}" if state_fips else ", all states")
            + (f", urban areas from {urban_area_year}" if urban_area_year else "")
            + (" (overwrite)" if overwrite else "")
            + "..."
        )

        service = UrbanicityClassificationService()
        result = service.classify(
            year=year,
            state_fips=state_fips,
            urban_area_year=urban_area_year,
            dataset=dataset,
            batch_size=batch_size,
            overwrite=overwrite,
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"  Classified:           {result.classified}")
        )
        self.stdout.write(f"  Skipped (no pop):     {result.skipped_no_population}")
        self.stdout.write(f"  Skipped (no UA):      {result.skipped_no_urban_area}")
        self.stdout.write(f"  Skipped (no point):   {result.skipped_no_point}")
        self.stdout.write(f"  Total processed:      {result.total_processed}")

        if result.errors:
            self.stdout.write(
                self.style.WARNING(f"  Errors:               {len(result.errors)}")
            )
            for err in result.errors[:10]:
                self.stdout.write(self.style.ERROR(f"    - {err}"))
            if len(result.errors) > 10:
                self.stdout.write(
                    self.style.WARNING(
                        f"    ... and {len(result.errors) - 10} more"
                    )
                )
