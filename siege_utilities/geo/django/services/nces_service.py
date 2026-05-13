"""
Service for populating NCES education data into Django models.

Downloads NCES locale boundaries, school locations, and district data
using NCESDownloader, then loads into NCESLocaleBoundary, SchoolLocation,
and enriches existing SchoolDistrict* records with locale codes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from django.db import transaction

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


@dataclass
class NCESPopulationResult:
    """Result of an NCES population operation."""

    action: str
    year: int
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return self.records_created + self.records_updated + self.records_skipped

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class NCESPopulationService:
    """Service for downloading and populating NCES education data.

    Three actions:
    1. populate_locale_boundaries — download 12 territory polygons per year
    2. populate_school_locations — download geocoded school points
    3. enrich_school_districts — match NCES data to existing district records

    Example::

        service = NCESPopulationService(cache_dir="/data/nces")
        result = service.populate_locale_boundaries(year=2023)
        print(f"Created {result.records_created} locale boundaries")
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir

    def _get_downloader(self):
        from siege_utilities.geo.providers.nces_download import NCESDownloader

        return NCESDownloader(cache_dir=self.cache_dir)

    @transaction.atomic
    def populate_locale_boundaries(
        self,
        year: int = 2023,
        update_existing: bool = False,
        batch_size: int = 100,
    ) -> NCESPopulationResult:
        """Download and populate NCESLocaleBoundary records.

        Args:
            year: NCES publication year.
            update_existing: If True, update existing records.
            batch_size: Records per database batch.

        Returns:
            NCESPopulationResult with statistics.
        """
        from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
        from django.utils import timezone

        from siege_utilities.conf import settings

        from ..models import NCESLocaleBoundary

        result = NCESPopulationResult(action="locale_boundaries", year=year)

        try:
            downloader = self._get_downloader()
            gdf = downloader.download_locale_boundaries(year)
        except Exception as e:
            log.error(f"Failed to download locale boundaries: {e}")
            result.errors.append(str(e))
            return result

        existing_by_key = {
            (obj.locale_code, obj.nces_year): obj
            for obj in NCESLocaleBoundary.objects.filter(nces_year=year)
        }

        objects_to_create: list = []
        objects_to_update: list = []
        # bulk_update bypasses auto_now=True; set updated_at explicitly.
        now = timezone.now()
        _UPDATE_FIELDS = (
            "locale_category", "locale_subcategory", "name",
            "vintage_year", "geometry", "source", "updated_at",
        )

        for idx, row in gdf.iterrows():
            try:
                locale_code = int(row["locale_code"])
                existing = existing_by_key.get((locale_code, year))

                if existing and not update_existing:
                    result.records_skipped += 1
                    continue

                geom = GEOSGeometry(row.geometry.wkt, srid=settings.STORAGE_CRS)
                if geom.geom_type == "Polygon":
                    geom = MultiPolygon(geom, srid=settings.STORAGE_CRS)

                kwargs = {
                    "locale_code": locale_code,
                    "locale_category": row.get("locale_category", ""),
                    "locale_subcategory": row.get("locale_subcategory", ""),
                    "nces_year": year,
                    "name": row.get("name", f"Locale {locale_code}"),
                    "vintage_year": year,
                    "geometry": geom,
                    "source": "NCES EDGE",
                }

                if existing:
                    for key, value in kwargs.items():
                        setattr(existing, key, value)
                    existing.updated_at = now
                    objects_to_update.append(existing)
                    if len(objects_to_update) >= batch_size:
                        NCESLocaleBoundary.objects.bulk_update(
                            objects_to_update, list(_UPDATE_FIELDS),
                        )
                        result.records_updated += len(objects_to_update)
                        objects_to_update = []
                else:
                    objects_to_create.append(NCESLocaleBoundary(**kwargs))
                    if len(objects_to_create) >= batch_size:
                        NCESLocaleBoundary.objects.bulk_create(
                            objects_to_create, ignore_conflicts=True
                        )
                        result.records_created += len(objects_to_create)
                        objects_to_create = []

            except Exception as e:
                log.error(f"Error processing locale boundary {idx}: {e}")
                result.errors.append(f"Locale {idx}: {e}")

        if objects_to_create:
            NCESLocaleBoundary.objects.bulk_create(
                objects_to_create, ignore_conflicts=True
            )
            result.records_created += len(objects_to_create)

        if objects_to_update:
            NCESLocaleBoundary.objects.bulk_update(
                objects_to_update, list(_UPDATE_FIELDS),
            )
            result.records_updated += len(objects_to_update)

        log.info(
            f"Populated locale boundaries: {result.records_created} created, "
            f"{result.records_updated} updated, {result.records_skipped} skipped"
        )
        return result

    @transaction.atomic
    def populate_school_locations(
        self,
        year: int = 2023,
        state_fips: Optional[str] = None,
        update_existing: bool = False,
        batch_size: int = 500,
    ) -> NCESPopulationResult:
        """Download and populate SchoolLocation records.

        Args:
            year: NCES publication year.
            state_fips: 2-digit FIPS code or 2-letter abbreviation to filter.
            update_existing: If True, update existing records.
            batch_size: Records per database batch.

        Returns:
            NCESPopulationResult with statistics.
        """
        from django.contrib.gis.geos import Point
        from django.utils import timezone

        from ..models import SchoolLocation, State

        result = NCESPopulationResult(action="school_locations", year=year)

        # Resolve state abbreviation from FIPS if needed
        state_abbr = None
        if state_fips:
            try:
                state_obj = State.objects.filter(state_fips=state_fips).first()
                if state_obj and hasattr(state_obj, "abbreviation"):
                    state_abbr = state_obj.abbreviation
                else:
                    state_abbr = state_fips  # Might already be abbreviation
            except Exception:
                state_abbr = state_fips

        try:
            downloader = self._get_downloader()
            gdf = downloader.download_school_locations(year, state_abbr=state_abbr)
        except Exception as e:
            log.error(f"Failed to download school locations: {e}")
            result.errors.append(str(e))
            return result

        # Build state lookup for FKs
        state_cache = {}
        for st in State.objects.all():
            state_cache[st.state_fips] = st
            if hasattr(st, "abbreviation"):
                state_cache[st.abbreviation] = st

        existing_by_key = {
            (obj.ncessch, obj.vintage_year): obj
            for obj in SchoolLocation.objects.filter(vintage_year=year)
        }

        objects_to_create: list = []
        objects_to_update: list = []
        now = timezone.now()
        _UPDATE_FIELDS = (
            "school_name", "lea_id", "state", "locale_code",
            "locale_category", "locale_subcategory", "name",
            "vintage_year", "geometry", "source", "updated_at",
        )

        for idx, row in gdf.iterrows():
            try:
                ncessch = str(row.get("ncessch", ""))
                if not ncessch:
                    result.records_skipped += 1
                    continue

                existing = existing_by_key.get((ncessch, year))

                if existing and not update_existing:
                    result.records_skipped += 1
                    continue

                # Build point geometry
                geom = Point(
                    float(row.geometry.x),
                    float(row.geometry.y),
                    srid=4326,
                )

                # Resolve state FK
                state_obj = None
                sa = row.get("state_abbr", "")
                if sa:
                    state_obj = state_cache.get(str(sa).upper())

                locale_code = row.get("locale_code")
                if locale_code is not None:
                    try:
                        locale_code = int(locale_code)
                    except (ValueError, TypeError):
                        locale_code = None

                kwargs = {
                    "ncessch": ncessch,
                    "school_name": str(row.get("school_name", ""))[:255],
                    "lea_id": str(row.get("lea_id", ""))[:7],
                    "state": state_obj,
                    "locale_code": locale_code,
                    "locale_category": str(row.get("locale_category", "")),
                    "locale_subcategory": str(row.get("locale_subcategory", "")),
                    "name": str(row.get("school_name", ""))[:255],
                    "vintage_year": year,
                    "geometry": geom,
                    "source": "NCES EDGE",
                }

                if existing:
                    for key, value in kwargs.items():
                        setattr(existing, key, value)
                    existing.updated_at = now
                    objects_to_update.append(existing)
                    if len(objects_to_update) >= batch_size:
                        SchoolLocation.objects.bulk_update(
                            objects_to_update, list(_UPDATE_FIELDS),
                        )
                        result.records_updated += len(objects_to_update)
                        objects_to_update = []
                else:
                    objects_to_create.append(SchoolLocation(**kwargs))
                    if len(objects_to_create) >= batch_size:
                        SchoolLocation.objects.bulk_create(
                            objects_to_create, ignore_conflicts=True
                        )
                        result.records_created += len(objects_to_create)
                        objects_to_create = []

            except Exception as e:
                log.error(f"Error processing school {idx}: {e}")
                result.errors.append(f"School {idx}: {e}")

        if objects_to_create:
            SchoolLocation.objects.bulk_create(
                objects_to_create, ignore_conflicts=True
            )
            result.records_created += len(objects_to_create)

        if objects_to_update:
            SchoolLocation.objects.bulk_update(
                objects_to_update, list(_UPDATE_FIELDS),
            )
            result.records_updated += len(objects_to_update)

        log.info(
            f"Populated school locations: {result.records_created} created, "
            f"{result.records_updated} updated, {result.records_skipped} skipped"
        )
        return result

    def enrich_school_districts(
        self,
        year: int = 2023,
        update_existing: bool = False,
    ) -> NCESPopulationResult:
        """Enrich existing SchoolDistrict* records with NCES locale codes.

        Matches NCES district administrative data to existing Django
        SchoolDistrictElementary/Secondary/Unified records by LEA ID,
        then updates locale_code, locale_category, and locale_subcategory.

        Args:
            year: NCES publication year.
            update_existing: If True, overwrite existing locale codes.

        Returns:
            NCESPopulationResult with statistics.
        """
        from django.utils import timezone

        from ..models import (
            SchoolDistrictElementary,
            SchoolDistrictSecondary,
            SchoolDistrictUnified,
        )

        result = NCESPopulationResult(action="enrich_districts", year=year)

        try:
            downloader = self._get_downloader()
            df = downloader.download_district_data(year)
        except Exception as e:
            log.error(f"Failed to download district data: {e}")
            result.errors.append(str(e))
            return result

        # Build lookup: lea_id → locale info.
        if {"lea_id", "locale_code"}.issubset(df.columns):
            mask = df["lea_id"].astype(str).str.len().gt(0) & df["locale_code"].notna()
            sub = df.loc[mask, ["lea_id", "locale_code", "locale_category", "locale_subcategory"]].fillna("")
            locale_lookup = {
                str(lea): {
                    "locale_code": str(int(code)),
                    "locale_category": str(cat),
                    "locale_subcategory": str(sub_),
                }
                for lea, code, cat, sub_ in zip(
                    sub["lea_id"], sub["locale_code"],
                    sub["locale_category"], sub["locale_subcategory"],
                )
            }
        else:
            locale_lookup = {}

        # bulk_update bypasses auto_now=True; set updated_at explicitly.
        now = timezone.now()
        _UPDATE_FIELDS = (
            "locale_code", "locale_category", "locale_subcategory", "updated_at",
        )
        _BATCH = 500

        for model_cls in (
            SchoolDistrictElementary,
            SchoolDistrictSecondary,
            SchoolDistrictUnified,
        ):
            qs = model_cls.objects.all()
            if not update_existing:
                qs = qs.filter(locale_code="")

            to_update: list = []
            for district in qs.iterator():
                locale_info = locale_lookup.get(district.lea_id)
                if locale_info:
                    district.locale_code = locale_info["locale_code"]
                    district.locale_category = locale_info["locale_category"]
                    district.locale_subcategory = locale_info["locale_subcategory"]
                    district.updated_at = now
                    to_update.append(district)
                    if len(to_update) >= _BATCH:
                        model_cls.objects.bulk_update(to_update, list(_UPDATE_FIELDS))
                        result.records_updated += len(to_update)
                        to_update = []
                else:
                    result.records_skipped += 1

            if to_update:
                model_cls.objects.bulk_update(to_update, list(_UPDATE_FIELDS))
                result.records_updated += len(to_update)

        log.info(
            f"Enriched school districts: {result.records_updated} updated, "
            f"{result.records_skipped} skipped"
        )
        return result
