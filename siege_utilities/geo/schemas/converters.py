"""
Conversion utilities between GeoDataFrame, Pydantic schemas, and Django ORM.

Three conversion directions:
    GeoDataFrame → Schema:  gdf_to_schemas(gdf, SchemaClass)
    Schema → ORM:           schemas_to_orm(schemas, ModelClass)
    ORM → GeoDataFrame:     orm_to_gdf(queryset)

For Django models, from_schema()/to_schema() classmethods are the idiomatic
way to do single-object conversions without importing converters directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    import geopandas as gpd
    from pydantic import BaseModel

T = TypeVar("T")


def schemas_to_gdf(
    schemas: list["BaseModel"],
    geometry_wkts: list[str] | None = None,
    geometry_column: str = "geometry",
    srid: int = 4326,
) -> "gpd.GeoDataFrame":
    """
    Convert a list of Pydantic schema instances to a GeoDataFrame.

    Complement to gdf_to_schemas(). No Django required.

    Args:
        schemas: List of Pydantic schema instances
        geometry_wkts: Optional list of WKT geometry strings (parallel to schemas)
        geometry_column: Name for the geometry column
        srid: SRID for the CRS (default 4326)

    Returns:
        GeoDataFrame with schema data and optional geometry
    """
    import geopandas as gpd
    import pandas as pd

    if not schemas:
        return gpd.GeoDataFrame()

    records = [s.model_dump() for s in schemas]
    df = pd.DataFrame(records)

    if geometry_wkts:
        from shapely import wkt

        geometries = []
        for i, row_wkt in enumerate(geometry_wkts):
            if row_wkt:
                geometries.append(wkt.loads(row_wkt))
            else:
                geometries.append(None)
        df[geometry_column] = geometries
        return gpd.GeoDataFrame(df, geometry=geometry_column, crs=f"EPSG:{srid}")

    return gpd.GeoDataFrame(df)


def gdf_to_schemas(
    gdf: "gpd.GeoDataFrame",
    schema_class: type[T],
    column_map: dict[str, str] | None = None,
) -> list[T]:
    """
    Convert a GeoDataFrame to a list of Pydantic schema instances.

    Geometry is dropped (schemas are non-spatial).  Column names are
    mapped via column_map or auto-matched to schema field names.

    Args:
        gdf: Input GeoDataFrame
        schema_class: Pydantic model class to instantiate
        column_map: Optional {gdf_column: schema_field} overrides

    Returns:
        List of validated schema instances
    """
    column_map = column_map or {}

    # Build effective mapping: explicit overrides + identity for matching names
    schema_fields = set(schema_class.model_fields.keys())
    effective_map = {}
    for col in gdf.columns:
        if col == "geometry":
            continue
        mapped = column_map.get(col, col)
        if mapped in schema_fields:
            effective_map[col] = mapped

    results = []
    for _, row in gdf.iterrows():
        data = {}
        for col, field_name in effective_map.items():
            val = row.get(col)
            # Convert numpy/pandas types to Python native
            if hasattr(val, "item"):
                val = val.item()
            if val is not None and str(val) != "nan":
                data[field_name] = val
        results.append(schema_class.model_validate(data))

    return results


def schemas_to_orm(
    schemas: list["BaseModel"],
    model_class: type,
    geometry_wkts: list[str] | None = None,
    srid: int = 4326,
) -> list:
    """
    Convert a list of Pydantic schemas to Django ORM model instances.

    Does NOT call save() — returns unsaved instances for bulk_create.

    Args:
        schemas: List of Pydantic schema instances
        model_class: Django model class to instantiate
        geometry_wkts: Optional list of WKT geometry strings (parallel to schemas)
        srid: SRID for geometry (default 4326)

    Returns:
        List of unsaved Django model instances
    """
    from django.contrib.gis.geos import GEOSGeometry

    instances = []
    for i, schema in enumerate(schemas):
        kwargs = schema.model_dump(exclude_none=True)

        # Remove schema-only fields not on the model
        kwargs.pop("internal_point_wkt", None)

        # Add geometry if provided
        if geometry_wkts and i < len(geometry_wkts) and geometry_wkts[i]:
            kwargs["geometry"] = GEOSGeometry(geometry_wkts[i], srid=srid)

        instances.append(model_class(**kwargs))

    return instances


def orm_to_gdf(
    queryset,
    geometry_field: str = "geometry",
    srid: int = 4326,
) -> "gpd.GeoDataFrame":
    """
    Convert a Django QuerySet to a GeoDataFrame.

    Args:
        queryset: Django QuerySet (must include geometry field)
        geometry_field: Name of the geometry field
        srid: SRID for the output CRS

    Returns:
        GeoDataFrame with geometry and all non-geometry fields
    """
    import geopandas as gpd
    from shapely import wkt

    records = []
    for obj in queryset:
        data = {}
        for field in obj._meta.get_fields():
            if not hasattr(field, "attname"):
                continue
            name = field.attname
            if name == geometry_field:
                geom = getattr(obj, geometry_field)
                data["geometry"] = wkt.loads(geom.wkt) if geom else None
            else:
                data[name] = getattr(obj, name, None)
        records.append(data)

    if not records:
        return gpd.GeoDataFrame()

    gdf = gpd.GeoDataFrame(records, crs=f"EPSG:{srid}")
    return gdf
