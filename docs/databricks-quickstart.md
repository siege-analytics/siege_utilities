# Databricks Quickstart

## Installation

### Job Cluster (init script or notebook)

```python
%pip install siege-utilities[databricks,geo,data]
```

### Cluster Library (recommended for shared clusters)

Add to cluster configuration → Libraries → Install New → PyPI:

```
siege-utilities[databricks,geo,data]
```

## Known-Good Runtime Combinations

| Databricks Runtime | Python | Status |
|--------------------|--------|--------|
| DBR 14.3 LTS | 3.11 | Tested |
| DBR 15.x | 3.11 | Expected compatible |
| DBR 13.x | 3.10 | Not tested (Python 3.10) |

## Module Overview

```python
from siege_utilities.databricks import (
    # Authentication
    get_workspace_client,       # WorkspaceClient (PAT, profile, Azure SP)

    # Spark session
    get_active_spark_session,   # Get or create Spark session
    get_dbutils,                # Get DBUtils handle

    # Secrets
    get_runtime_secret,         # Read runtime secrets
    runtime_secret_exists,      # Check if secret exists
    ensure_secret_scope,        # Create/verify secret scope
    put_secret,                 # Write workspace secrets

    # DataFrame conversions
    pandas_to_spark,            # Pandas → Spark
    spark_to_pandas,            # Spark → Pandas
    geopandas_to_spark,         # GeoPandas → Spark (geometry as WKT)
    spark_to_geopandas,         # Spark → GeoPandas (WKT → geometry)

    # LakeBase / PostgreSQL
    parse_conninfo,             # Parse connection strings
    build_jdbc_url,             # JDBC URL for PostgreSQL
    build_pgpass_entry,         # .pgpass format
    build_lakebase_psql_command,# psql CLI command

    # Unity Catalog
    build_foreign_table_sql,    # CREATE FOREIGN TABLE SQL
    build_schema_and_table_sync_sql,  # Schema + table sync

    # Artifacts
    build_databricks_run_url,   # Direct link to job run
)
```

## Common Patterns

### Census Boundary Retrieval on Cluster

```python
from siege_utilities.geo.spatial_data import CensusDataSource

source = CensusDataSource()
result = source.fetch_geographic_boundaries(2020, "county", state_fips="06")

if result.success:
    gdf = result.geodataframe
    # Convert to Spark for distributed processing
    from siege_utilities.databricks import geopandas_to_spark
    sdf = geopandas_to_spark(spark, gdf, geometry_format="wkt")
    sdf.createOrReplaceTempView("ca_counties")
else:
    print(f"Failed at {result.error_stage}: {result.message}")
```

### Secrets Management

```python
from siege_utilities.databricks import (
    get_runtime_secret,
    ensure_secret_scope,
    put_secret,
    get_workspace_client,
)

# Read a runtime secret (fast — uses dbutils)
api_key = get_runtime_secret("census", "api_key")

# Create scope + write secret (uses workspace API)
client = get_workspace_client(token="dapi...")
ensure_secret_scope(client, "census")
put_secret(client, "census", "api_key", "your-key-here")
```

### Spatial Loader Fallback

For loading shapefiles into Delta Lake, use the fallback planner:

```python
from siege_utilities.geo.databricks_fallback import select_spatial_loader

plan = select_spatial_loader(
    ogr2ogr_available=False,    # No GDAL on cluster
    sedona_available=True,       # Sedona jar installed
)
print(plan.primary_loader)      # "sedona"
print(plan.loader_order)        # ["sedona", "python"]
```

### DataFrame Bridge

```python
import pandas as pd
from siege_utilities.databricks import pandas_to_spark, spark_to_pandas

# Pandas → Spark
pdf = pd.DataFrame({"name": ["Alice", "Bob"], "score": [95, 87]})
sdf = pandas_to_spark(spark, pdf)

# Spark → Pandas (with row limit for large tables)
pdf_back = spark_to_pandas(sdf, limit=10000)
```

### Isochrones with Open-Source Providers

```python
import siege_utilities as su

# OpenRouteService hosted API
iso = su.get_isochrone(
    latitude=41.8781,
    longitude=-87.6298,
    travel_time_minutes=15,
    provider="openrouteservice",
    api_key="<ors-key>",
)

# Self-hosted Valhalla
iso_internal = su.get_isochrone(
    latitude=41.8781,
    longitude=-87.6298,
    travel_time_minutes=20,
    provider="valhalla",
    base_url="http://valhalla.svc.cluster.local:8002",
)
```

See `docs/ISOCHRONES_AND_WKLS.md` for provider behavior and WKLS integration guidance.

## Common Pitfalls

### GDAL Not Available

Standard Databricks runtimes do **not** include GDAL. This means:

- `fiona.open()` will fail
- Django GIS operations will fail
- `geopandas.read_file()` requires Fiona → GDAL

**Workaround:** Use `geopandas_to_spark()` with WKT geometry format to move
geo data between Pandas and Spark without Fiona. For reading shapefiles, download
them locally first and use the `select_spatial_loader()` fallback planner.

### Spark Session Already Active

On Databricks, a Spark session is always available as `spark`. The
`get_active_spark_session()` helper detects this and returns the existing session
rather than creating a new one.

```python
from siege_utilities.databricks import get_active_spark_session

# On Databricks: returns the existing cluster session
# Locally: creates a new SparkSession
spark = get_active_spark_session()
```

### Geometry Serialization

When converting GeoPandas to Spark, geometries are serialized as strings:

- `"wkt"` — Well-Known Text (human-readable, larger)
- `"wkb_hex"` — WKB hex (compact, faster)

```python
from siege_utilities.databricks import geopandas_to_spark

# WKT is more readable for debugging
sdf = geopandas_to_spark(spark, gdf, geometry_format="wkt")

# WKB hex is more efficient for storage
sdf = geopandas_to_spark(spark, gdf, geometry_format="wkb_hex")
```

### Unity Catalog Foreign Tables

For PostgreSQL foreign tables in Unity Catalog:

```python
from siege_utilities.databricks import build_foreign_table_sql

sql = build_foreign_table_sql(
    catalog="main",
    schema="lakebase",
    table="census_tracts",
    pg_schema="public",
    pg_table="census_tracts",
    connection_name="lakebase_prod",
)
spark.sql(sql)
```
