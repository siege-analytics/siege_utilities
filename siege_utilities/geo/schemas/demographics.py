"""
Pydantic schemas for demographic data models.

Mirrors the Django models in geo/django/models/demographics.py but with
plain strings (boundary_type + boundary_id) replacing Django's generic
foreign keys.  No Django dependency required.
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field, model_validator


DATASET_CHOICES = frozenset({"acs5", "acs1", "dec", "dec_pl"})


class DemographicVariableSchema(BaseModel):
    """Reference schema for a Census variable."""

    code: str = Field(max_length=20)
    label: str = Field(max_length=255)
    concept: str = ""
    dataset: str = Field(max_length=10)
    predicate_type: str = ""
    group: str = ""
    universe: str = ""

    model_config = {"from_attributes": True}

    @property
    def is_estimate(self) -> bool:
        """True if this is an estimate variable (ends in E)."""
        return self.code.endswith("E")

    @property
    def is_moe(self) -> bool:
        """True if this is a margin of error variable (ends in M)."""
        return self.code.endswith("M")

    @property
    def base_code(self) -> str:
        """Return the code without the E/M suffix."""
        if self.code.endswith(("E", "M")):
            return self.code[:-1]
        return self.code


class DemographicSnapshotSchema(BaseModel):
    """
    One demographic snapshot for a boundary.

    Uses boundary_type + boundary_id instead of Django's generic FK.
    """

    boundary_type: str = Field(max_length=30)
    boundary_id: str = Field(max_length=20)
    year: int = Field(ge=1990, le=2050)
    dataset: str = Field(max_length=10)
    vintage: Optional[int] = None

    values: dict[str, float | int | str] = Field(default_factory=dict)
    moe_values: dict[str, float | int | str] = Field(default_factory=dict)

    total_population: Optional[int] = None
    median_household_income: Optional[int] = None
    median_age: Optional[float] = None

    source_url: str = ""

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def auto_populate_summaries(self):
        """Auto-populate summary fields from values, mirroring Django save()."""
        if self.values:
            if "B01001_001E" in self.values and self.total_population is None:
                try:
                    self.total_population = int(self.values["B01001_001E"])
                except (ValueError, TypeError):
                    pass

            if "B19013_001E" in self.values and self.median_household_income is None:
                try:
                    self.median_household_income = int(self.values["B19013_001E"])
                except (ValueError, TypeError):
                    pass

            if "B01002_001E" in self.values and self.median_age is None:
                try:
                    self.median_age = float(self.values["B01002_001E"])
                except (ValueError, TypeError):
                    pass
        return self

    def get_value(self, variable_code: str, default=None):
        """Get a specific variable value."""
        return self.values.get(variable_code, default)

    def get_moe(self, variable_code: str, default=None):
        """Get margin of error for a specific variable."""
        code = variable_code.rstrip("E")
        return self.moe_values.get(f"{code}M", self.moe_values.get(code, default))


class DemographicTimeSeriesSchema(BaseModel):
    """Pre-computed time series for a single variable on a single boundary."""

    boundary_type: str = Field(max_length=30)
    boundary_id: str = Field(max_length=20)
    variable_code: str = Field(max_length=20)
    dataset: str = Field(max_length=10)

    start_year: int
    end_year: int
    years: list[int]
    values: list[float | int]
    moe_values: list[float | int | None] = Field(default_factory=list)

    mean_value: Optional[float] = None
    std_dev: Optional[float] = None
    cagr: Optional[float] = None
    trend_direction: str = ""

    model_config = {"from_attributes": True}
