"""
Management command to seed CongressionalTerm records.

Seeds all Congresses from the 1st (1789) through a configurable upper bound.
Uses the constitutional convention: each Congress is a 2-year term starting
January 3 of odd-numbered years (post-20th Amendment, effective 1935).

Before the 20th Amendment (Congresses 1-73), terms started March 4.

Usage:
    python manage.py populate_congressional_terms
    python manage.py populate_congressional_terms --through 130
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from siege_utilities.geo.django.models import CongressionalTerm


# Senate class rotation: Class I elected in years ≡ 0 mod 6 (2000, 2006, ...),
# Class II in years ≡ 2 mod 6, Class III in years ≡ 4 mod 6.
# Within the Founding-era pattern, assign classes by Congress number.
def _senate_classes_up(election_year: int) -> list:
    """Determine which Senate classes are up for election in a given year."""
    mod = election_year % 6
    if mod == 0:
        return [3]
    elif mod == 2:
        return [1]
    elif mod == 4:
        return [2]
    return []


def _generate_terms(through: int):
    """Generate CongressionalTerm data for Congresses 1 through `through`."""
    terms = []
    for n in range(1, through + 1):
        # Election year: the even year before the Congress starts
        # 1st Congress: election 1788, start 1789
        election_year = 1788 + (n - 1) * 2

        if n <= 73:
            # Pre-20th Amendment: terms start March 4
            start = date(1789 + (n - 1) * 2, 3, 4)
            end = date(1789 + n * 2 - 2 + 2, 3, 4)  # next Congress start
        else:
            # Post-20th Amendment: terms start January 3
            start_year = 1935 + (n - 73) * 2 - 2 + 1  # simplified
            # Direct calculation: Congress 73 starts 1933-03-04
            # Congress 74 starts 1935-01-03, Congress 75 starts 1937-01-03, etc.
            start_year = 1935 + (n - 74) * 2
            start = date(start_year, 1, 3)
            end = date(start_year + 2, 1, 3)

        is_presidential = (election_year % 4 == 0)
        senate_classes = _senate_classes_up(election_year)

        terms.append({
            "congress_number": n,
            "start_date": start,
            "end_date": end,
            "election_year": election_year,
            "is_presidential": is_presidential,
            "senate_classes_up": senate_classes,
        })

    return terms


class Command(BaseCommand):
    """Seed CongressionalTerm records from the 1st Congress through present."""

    help = "Populate CongressionalTerm records (1st Congress through specified)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--through",
            type=int,
            default=119,
            help="Highest Congress number to seed (default: 119, the current Congress)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing records instead of skipping them",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        through = options["through"]
        update = options["update"]

        self.stdout.write(f"Seeding CongressionalTerm records 1 through {through}...")

        terms_data = _generate_terms(through)
        created = 0
        updated = 0
        skipped = 0

        for data in terms_data:
            congress_number = data.pop("congress_number")

            if update:
                obj, was_created = CongressionalTerm.objects.update_or_create(
                    congress_number=congress_number,
                    defaults=data,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            else:
                _, was_created = CongressionalTerm.objects.get_or_create(
                    congress_number=congress_number,
                    defaults=data,
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done: {created} created, {updated} updated, {skipped} skipped"
        ))
