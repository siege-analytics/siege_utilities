"""
Management command to populate Census demographic data.

Usage:
    python manage.py populate_demographics --year 2022 --type tract --state 06 --variables income
    python manage.py populate_demographics --year 2022 --type county --state 06 --variables all

Configure the API key through CENSUS_API_KEY; --api-key is rejected to keep
credentials out of process listings and scheduler command logs.
"""

import logging
import os

from django.core.management.base import BaseCommand, CommandError

from siege_utilities.geo.django.services import DemographicPopulationService

__all__ = ['Command']

logger = logging.getLogger(__name__)


def _reject_cli_api_key(value: str) -> None:
    # Reject the legacy option without argparse echoing its secret value.
    message = "--api-key is no longer supported; set CENSUS_API_KEY in the environment"
    logger.error(message)
    raise CommandError(message)


class Command(BaseCommand):
    """Populate Census demographic data from Census API."""

    help = "Populate Census demographic data from Census API"

    GEOGRAPHY_TYPES = ["state", "county", "tract", "blockgroup", "place"]
    VARIABLE_GROUPS = [
        "total_population",
        "demographics_basic",
        "race_ethnicity",
        "income",
        "education",
        "poverty",
        "housing",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-partial",
            action="store_true",
            help="Allow reported errors if at least one record was created or updated",
        )
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="ACS/Census year (e.g., 2022)",
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
            required=True,
            help="State FIPS code or abbreviation",
        )
        parser.add_argument(
            "--variables",
            type=str,
            required=True,
            choices=self.VARIABLE_GROUPS + ["all"],
            help="Variable group to fetch",
        )
        parser.add_argument(
            "--dataset",
            type=str,
            default="acs5",
            choices=["acs5", "acs1", "dec"],
            help="Census dataset (default: acs5)",
        )
        parser.add_argument(
            "--api-key",
            type=_reject_cli_api_key,
            help="Removed; set CENSUS_API_KEY in the environment",
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

    def _normalize_state(self, state_input: str) -> str:
        """Convert state input to FIPS code."""
        if state_input.isdigit() and len(state_input) == 2:
            return state_input

        if state_input.isdigit() and len(state_input) == 1:
            return state_input.zfill(2)

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
        state_input = options["state"]
        variables = options["variables"]
        dataset = options.get("dataset", "acs5")
        if options.get("api_key") is not None:
            _reject_cli_api_key(options["api_key"])
        api_key = os.environ.get("CENSUS_API_KEY")
        update_existing = options.get("update", False)
        batch_size = options.get("batch_size", 500)

        state_fips = self._normalize_state(state_input)

        service = DemographicPopulationService(api_key=api_key)

        if variables == "all":
            groups_to_process = self.VARIABLE_GROUPS
        else:
            groups_to_process = [variables]

        total_created = 0
        total_updated = 0
        total_errors = []

        for group in groups_to_process:
            self.stdout.write(
                f"Fetching {group} data for {geo_type} in state {state_fips}..."
            )

            result = service.populate(
                geography_type=geo_type,
                year=year,
                state_fips=state_fips,
                variable_group=group,
                dataset=dataset,
                update_existing=update_existing,
                batch_size=batch_size,
            )

            total_created += result.records_created
            total_updated += result.records_updated
            total_errors.extend(result.errors)

            if result.success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {group}: {result.records_created} created, "
                        f"{result.records_updated} updated, "
                        f"{result.records_skipped} skipped"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"  {group}: {len(result.errors)} errors")
                )
                for error in result.errors[:5]:
                    self.stdout.write(self.style.ERROR(f"    - {error}"))

        # Summary
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Total: {total_created} created, {total_updated} updated"
            )
        )

        if total_errors:
            self.stdout.write(
                self.style.WARNING(f"Total errors: {len(total_errors)}")
            )
            if not options.get("allow_partial", False) or total_created + total_updated == 0:
                raise CommandError(
                    f"Demographic population failed with {len(total_errors)} errors"
                )
