"""
Management command to populate Census boundary data from TIGER/Line.

Usage:
    python manage.py populate_boundaries --year 2020 --type county
    python manage.py populate_boundaries --year 2020 --type tract --state 06
    python manage.py populate_boundaries --year 2020 --type tract --state CA
    python manage.py populate_boundaries --year 2020 --type all --state 06

Any skipped row or reported error makes the command exit nonzero after the
counts are printed. Use --allow-partial to tolerate errors or skipped rows
when at least one record was created or updated. Known unpublished VTD sources
are warned and skipped without failing. Use --update when reloading boundaries.
"""

from typing import Optional

from django.core.management.base import BaseCommand, CommandError

from siege_utilities.geo.boundary_result import BoundaryRetrievalError
from siege_utilities.geo.django.services import BoundaryPopulationService

__all__ = ['Command']


class Command(BaseCommand):
    """Populate Census boundary data from TIGER/Line shapefiles."""

    help = "Populate Census boundary data from TIGER/Line shapefiles"

    GEOGRAPHY_TYPES = [
        "state",
        "county",
        "tract",
        "blockgroup",
        "block",
        "place",
        "zcta",
        "cd",
        "sldu",
        "sldl",
        "vtd",
        "cbsa",
        "urbanarea",
        "elsd",
        "scsd",
        "unsd",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-partial",
            action="store_true",
            help="Allow errors or skipped rows if at least one record was created or updated",
        )
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="Census year (e.g., 2020, 2010)",
        )
        parser.add_argument(
            "--type",
            type=str,
            required=True,
            choices=self.GEOGRAPHY_TYPES + ["all"],
            help="Geography type to populate",
        )
        parser.add_argument(
            "--state",
            type=str,
            help="State FIPS code or abbreviation (required for state-scoped files)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing records instead of skipping",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for database operations",
        )
        parser.add_argument(
            "--link-parents",
            action="store_true",
            help="Link child boundaries to parent boundaries after population",
        )

    def _normalize_state(self, state_input: str) -> Optional[str]:
        """Convert state input to FIPS code."""
        if not state_input:
            return None

        # If already a 2-digit FIPS code
        if state_input.isdigit() and len(state_input) == 2:
            return state_input

        # Zero-pad single digit
        if state_input.isdigit() and len(state_input) == 1:
            return state_input.zfill(2)

        # Try to convert abbreviation to FIPS
        from siege_utilities.geo import normalize_state_identifier

        try:
            return normalize_state_identifier(state_input)
        except (ValueError, KeyError) as e:
            raise CommandError(
                f"Invalid state identifier: {state_input}. "
                "Use FIPS code (e.g., 06) or abbreviation (e.g., CA)"
            ) from e

    def handle(self, *args, **options):
        year = options["year"]
        geo_type = options["type"]
        state_input = options.get("state")
        update_existing = options.get("update", False)
        batch_size = options.get("batch_size", 500)
        link_parents = options.get("link_parents", False)

        # Normalize state
        state_fips = self._normalize_state(state_input) if state_input else None

        # Check required state for sub-state geographies
        requires_state = ["tract", "blockgroup", "block"]
        if geo_type in requires_state and not state_fips:
            raise CommandError(
                f"--state is required for geography type '{geo_type}'"
            )

        service = BoundaryPopulationService()

        if geo_type == "all":
            # Populate all types in order
            types_to_process = self.GEOGRAPHY_TYPES
        else:
            types_to_process = [geo_type]

        total_created = 0
        total_updated = 0
        total_skipped = 0
        total_sources_skipped = 0
        total_errors = []

        for gtype in types_to_process:
            # Skip types that require state if no state provided
            if gtype in requires_state and not state_fips:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping {gtype}: requires --state parameter"
                    )
                )
                continue

            self.stdout.write(f"Populating {gtype} boundaries for year {year}...")

            try:
                result = service.populate(
                    geography_type=gtype,
                    year=year,
                    state_fips=state_fips,
                    update_existing=update_existing,
                    batch_size=batch_size,
                )
            except BoundaryRetrievalError as exc:
                raise CommandError(f"{gtype} population failed: {exc}") from exc

            total_created += result.records_created
            total_updated += result.records_updated
            total_skipped += result.records_skipped
            total_sources_skipped += result.sources_skipped
            total_errors.extend(result.errors)

            for warning in result.warnings:
                self.stdout.write(self.style.WARNING(f"  {warning}"))

            style = self.style.ERROR if result.errors or result.records_skipped else self.style.SUCCESS
            self.stdout.write(style(
                f"  {gtype}: {result.records_created} created, "
                f"{result.records_updated} updated, "
                f"{result.records_skipped + result.sources_skipped} skipped, "
                f"{len(result.errors)} errors"
            ))
            for error in result.errors[:5]:  # Show first 5 errors
                self.stdout.write(self.style.ERROR(f"    - {error}"))

            # Link parents if requested
            if link_parents and gtype != "state" and not result.sources_skipped:
                linked = service.link_parent_relationships(gtype, year, state_fips)
                if linked:
                    self.stdout.write(
                        self.style.SUCCESS(f"  Linked {linked} parent relationships")
                    )

        # Summary
        self.stdout.write("")
        style = self.style.ERROR if total_errors or total_skipped else self.style.SUCCESS
        self.stdout.write(
            style(
                f"Total: {total_created} created, {total_updated} updated, "
                f"{total_skipped + total_sources_skipped} skipped"
            )
        )

        if total_errors:
            self.stdout.write(
                self.style.WARNING(f"Total errors: {len(total_errors)}")
            )

        if (total_errors or total_skipped) and (
            not options.get("allow_partial", False) or total_created + total_updated == 0
        ):
            raise CommandError(
                f"Boundary population incomplete: {total_skipped} skipped, "
                f"{len(total_errors)} errors"
            )
