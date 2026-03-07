"""
Service for populating TimezoneGeometry from timezone-boundary-builder GeoJSON.

Data source: https://github.com/evansiroky/timezone-boundary-builder
Releases provide GeoJSON files with IANA timezone boundaries.
"""

import json
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from django.db import transaction

log = logging.getLogger(__name__)

# timezone-boundary-builder release URL template
TBB_RELEASE_URL = (
    "https://github.com/evansiroky/timezone-boundary-builder/"
    "releases/download/{version}/timezones-with-oceans.geojson.zip"
)

# Standard timezone UTC offsets (partial list — covers US + common zones)
# Full precision requires pytz/zoneinfo, but this gives a good default.
TIMEZONE_OFFSETS = {
    "America/New_York": (-5.0, -4.0, True),
    "America/Chicago": (-6.0, -5.0, True),
    "America/Denver": (-7.0, -6.0, True),
    "America/Los_Angeles": (-8.0, -7.0, True),
    "America/Anchorage": (-9.0, -8.0, True),
    "Pacific/Honolulu": (-10.0, -10.0, False),
    "America/Phoenix": (-7.0, -7.0, False),
    "America/Puerto_Rico": (-4.0, -4.0, False),
    "Pacific/Guam": (10.0, 10.0, False),
    "Pacific/Samoa": (-11.0, -11.0, False),
    "Europe/London": (0.0, 1.0, True),
    "Europe/Berlin": (1.0, 2.0, True),
    "Europe/Moscow": (3.0, 3.0, False),
    "Asia/Tokyo": (9.0, 9.0, False),
    "Asia/Shanghai": (8.0, 8.0, False),
    "Australia/Sydney": (11.0, 10.0, True),
}


@dataclass
class TimezonePopulationResult:
    """Result of a timezone population run."""

    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class TimezonePopulationService:
    """
    Populate TimezoneGeometry model from timezone-boundary-builder GeoJSON.

    Example:
        >>> service = TimezonePopulationService()
        >>> result = service.populate_from_geojson('/path/to/timezones.geojson')
        >>> print(f"Created {result.records_created} timezone boundaries")
    """

    def populate_from_geojson(
        self,
        geojson_path: Union[str, Path],
        vintage_year: int = 2024,
        update_existing: bool = False,
        batch_size: int = 100,
    ) -> TimezonePopulationResult:
        """
        Populate TimezoneGeometry records from a GeoJSON file.

        Args:
            geojson_path: Path to the timezone-boundary-builder GeoJSON file.
            vintage_year: Vintage year for the records.
            update_existing: If True, update existing records.
            batch_size: Bulk create batch size.

        Returns:
            TimezonePopulationResult with counts.
        """
        from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

        from ..models.timezone import TimezoneGeometry

        result = TimezonePopulationResult()
        geojson_path = Path(geojson_path)

        if not geojson_path.exists():
            result.errors.append(f"File not found: {geojson_path}")
            return result

        # Handle .zip files
        if geojson_path.suffix == ".zip":
            with zipfile.ZipFile(geojson_path) as zf:
                geojson_names = [n for n in zf.namelist() if n.endswith(".geojson")]
                if not geojson_names:
                    result.errors.append("No .geojson file found in zip")
                    return result
                data = json.loads(zf.read(geojson_names[0]))
        else:
            with open(geojson_path) as f:
                data = json.load(f)

        features = data.get("features", [])
        log.info(f"Processing {len(features)} timezone features")

        with transaction.atomic():
            to_create = []
            for feature in features:
                props = feature.get("properties", {})
                tz_id = props.get("tzid")
                if not tz_id:
                    result.records_skipped += 1
                    continue

                existing = TimezoneGeometry.objects.filter(
                    timezone_id=tz_id,
                    vintage_year=vintage_year,
                ).first()

                if existing and not update_existing:
                    result.records_skipped += 1
                    continue

                # Parse geometry
                try:
                    geom = GEOSGeometry(json.dumps(feature["geometry"]))
                    if not isinstance(geom, MultiPolygon):
                        geom = MultiPolygon(geom)
                except Exception as e:
                    result.errors.append(f"Geometry error for {tz_id}: {e}")
                    continue

                # Look up UTC offset metadata
                offsets = TIMEZONE_OFFSETS.get(tz_id)
                if offsets:
                    utc_std, utc_dst, obs_dst = offsets
                else:
                    utc_std, utc_dst, obs_dst = self._lookup_offset(tz_id)

                if existing:
                    existing.geometry = geom
                    existing.utc_offset_std = utc_std
                    existing.utc_offset_dst = utc_dst
                    existing.observes_dst = obs_dst
                    existing.save()
                    result.records_updated += 1
                else:
                    to_create.append(
                        TimezoneGeometry(
                            timezone_id=tz_id,
                            feature_id=tz_id,
                            boundary_id=tz_id,
                            name=tz_id,
                            vintage_year=vintage_year,
                            source="timezone-boundary-builder",
                            geometry=geom,
                            utc_offset_std=utc_std,
                            utc_offset_dst=utc_dst,
                            observes_dst=obs_dst,
                        )
                    )

            if to_create:
                for i in range(0, len(to_create), batch_size):
                    batch = to_create[i : i + batch_size]
                    TimezoneGeometry.objects.bulk_create(
                        batch, ignore_conflicts=True
                    )
                result.records_created = len(to_create)

        log.info(
            f"Timezone populate: created={result.records_created}, "
            f"updated={result.records_updated}, skipped={result.records_skipped}"
        )
        return result

    def _lookup_offset(self, tz_id: str):
        """
        Attempt to resolve UTC offset from the standard library zoneinfo.

        Returns (utc_offset_std, utc_offset_dst, observes_dst) tuple.
        Falls back to (None, None, True) if resolution fails.
        """
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(tz_id)
            # January for standard time
            jan = datetime(2024, 1, 15, 12, 0, tzinfo=tz)
            # July for DST
            jul = datetime(2024, 7, 15, 12, 0, tzinfo=tz)

            std_offset = jan.utcoffset().total_seconds() / 3600
            dst_offset = jul.utcoffset().total_seconds() / 3600
            observes_dst = abs(std_offset - dst_offset) > 0.1

            return std_offset, dst_offset, observes_dst
        except Exception:
            return None, None, True
