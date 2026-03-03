"""
DataSource registry for managing external data provider configurations.

Provides a YAML-backed registry of data sources with built-in entries
for FEC, Census, NLRB, and NCES. Supports filtering by type and jurisdiction.
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .models.data_sources import (
    DataSource,
    DataSourceStatus,
    DataSourceType,
    Jurisdiction,
    JurisdictionLevel,
    SourceCredential,
)


# Built-in data source definitions
_BUILTIN_SOURCES: List[DataSource] = [
    DataSource(
        source_id="fec",
        name="Federal Election Commission",
        source_type=DataSourceType.CAMPAIGN_FINANCE,
        jurisdiction=Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal"),
        base_url="https://www.fec.gov/data/",
        documentation_url="https://api.open.fec.gov/developers/",
        status=DataSourceStatus.ACTIVE,
        auth_required=True,
        auth_type="api_key",
        file_formats=["fec", "csv", "json"],
        update_frequency="daily",
    ),
    DataSource(
        source_id="census",
        name="U.S. Census Bureau",
        source_type=DataSourceType.BOUNDARY,
        jurisdiction=Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal"),
        base_url="https://www2.census.gov/",
        documentation_url="https://www.census.gov/data/developers.html",
        status=DataSourceStatus.ACTIVE,
        auth_required=True,
        auth_type="api_key",
        file_formats=["shapefile", "geojson", "csv"],
        update_frequency="annual",
    ),
    DataSource(
        source_id="nlrb",
        name="National Labor Relations Board",
        source_type=DataSourceType.LABOR,
        jurisdiction=Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal"),
        base_url="https://www.nlrb.gov/",
        documentation_url="https://www.nlrb.gov/reports/open-data",
        status=DataSourceStatus.ACTIVE,
        auth_required=False,
        file_formats=["csv", "json"],
        update_frequency="quarterly",
    ),
    DataSource(
        source_id="nces",
        name="National Center for Education Statistics",
        source_type=DataSourceType.EDUCATION,
        jurisdiction=Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal"),
        base_url="https://nces.ed.gov/",
        documentation_url="https://nces.ed.gov/ccd/",
        status=DataSourceStatus.ACTIVE,
        auth_required=False,
        file_formats=["csv", "xlsx"],
        update_frequency="annual",
    ),
    DataSource(
        source_id="tx_ethics",
        name="Texas Ethics Commission",
        source_type=DataSourceType.CAMPAIGN_FINANCE,
        jurisdiction=Jurisdiction(
            level=JurisdictionLevel.STATE,
            state_fips="48",
            state_abbreviation="TX",
            name="Texas",
        ),
        base_url="https://www.ethics.state.tx.us/",
        status=DataSourceStatus.PLANNED,
        auth_required=False,
        file_formats=["csv"],
        notes="Requires research — data access not yet confirmed",
    ),
    DataSource(
        source_id="fl_elections",
        name="Florida Division of Elections",
        source_type=DataSourceType.CAMPAIGN_FINANCE,
        jurisdiction=Jurisdiction(
            level=JurisdictionLevel.STATE,
            state_fips="12",
            state_abbreviation="FL",
            name="Florida",
        ),
        base_url="https://dos.fl.gov/elections/",
        status=DataSourceStatus.PLANNED,
        auth_required=False,
        file_formats=["csv"],
        notes="Requires research — data access not yet confirmed",
    ),
]


class DataSourceRegistry:
    """
    Registry of external data sources.

    Loads built-in sources on init and optionally overlays a YAML file
    for user-defined sources and overrides.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self._sources: Dict[str, DataSource] = {}
        self._credentials: Dict[str, List[SourceCredential]] = {}

        # Load built-in sources
        for source in _BUILTIN_SOURCES:
            self._sources[source.source_id] = source

        # Overlay from YAML if provided
        if config_path is not None:
            self.load_from_yaml(config_path)

    def register_source(self, source: DataSource) -> None:
        """Register or update a data source."""
        self._sources[source.source_id] = source

    def get_source(self, source_id: str) -> Optional[DataSource]:
        """Get a data source by ID."""
        return self._sources.get(source_id)

    def list_sources(self, include_planned: bool = True) -> List[DataSource]:
        """List all registered sources, optionally filtering out planned ones."""
        sources = list(self._sources.values())
        if not include_planned:
            sources = [s for s in sources if s.status != DataSourceStatus.PLANNED]
        return sorted(sources, key=lambda s: s.source_id)

    def list_by_type(self, source_type: DataSourceType) -> List[DataSource]:
        """List sources filtered by type."""
        return sorted(
            [s for s in self._sources.values() if s.source_type == source_type],
            key=lambda s: s.source_id,
        )

    def list_by_jurisdiction(
        self,
        level: Optional[JurisdictionLevel] = None,
        state_abbreviation: Optional[str] = None,
    ) -> List[DataSource]:
        """List sources filtered by jurisdiction level and/or state."""
        results = list(self._sources.values())
        if level is not None:
            results = [s for s in results if s.jurisdiction.level == level]
        if state_abbreviation is not None:
            results = [
                s for s in results
                if s.jurisdiction.state_abbreviation == state_abbreviation
            ]
        return sorted(results, key=lambda s: s.source_id)

    def list_active(self) -> List[DataSource]:
        """List only active sources."""
        return sorted(
            [s for s in self._sources.values() if s.status == DataSourceStatus.ACTIVE],
            key=lambda s: s.source_id,
        )

    # Credential management

    def register_credential(self, credential: SourceCredential) -> None:
        """Register a credential for a source."""
        if credential.source_id not in self._credentials:
            self._credentials[credential.source_id] = []
        # Replace existing for same source+environment
        self._credentials[credential.source_id] = [
            c for c in self._credentials[credential.source_id]
            if c.environment != credential.environment
        ]
        self._credentials[credential.source_id].append(credential)

    def get_credential(
        self, source_id: str, environment: str = "production"
    ) -> Optional[SourceCredential]:
        """Get credential for a source in a given environment."""
        creds = self._credentials.get(source_id, [])
        for c in creds:
            if c.environment == environment:
                return c
        return None

    # YAML persistence

    def load_from_yaml(self, path: Path) -> None:
        """Load sources and credentials from a YAML file."""
        path = Path(path)
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text())
        if not data:
            return

        for entry in data.get("sources", []):
            source = DataSource(**entry)
            self._sources[source.source_id] = source

        for entry in data.get("credentials", []):
            cred = SourceCredential(**entry)
            self.register_credential(cred)

    def save_to_yaml(self, path: Path) -> None:
        """Save all sources and credentials to a YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "sources": [s.model_dump(mode="json") for s in self.list_sources()],
            "credentials": [],
        }
        for creds in self._credentials.values():
            for c in creds:
                data["credentials"].append(c.model_dump(mode="json"))

        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def __len__(self) -> int:
        return len(self._sources)

    def __contains__(self, source_id: str) -> bool:
        return source_id in self._sources
