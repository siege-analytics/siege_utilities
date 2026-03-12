"""
3D map rendering utilities using pydeck (deck.gl).

Provides hexagonal binning, column layers, and extruded choropleth maps
for Jupyter notebooks, Databricks, and standalone HTML export.

Requires the ``pydeck`` package (available via the ``[3d]`` or ``[streamlit]``
optional-dependency groups).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency guards
# ---------------------------------------------------------------------------

try:
    import pydeck as pdk
    PYDECK_AVAILABLE = True
except ImportError:
    PYDECK_AVAILABLE = False
    pdk = None

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    gpd = None

# ---------------------------------------------------------------------------
# Map styles
# ---------------------------------------------------------------------------

MAP_STYLES = {
    "dark": "mapbox://styles/mapbox/dark-v11",
    "light": "mapbox://styles/mapbox/light-v11",
    "satellite": "mapbox://styles/mapbox/satellite-v9",
    "streets": "mapbox://styles/mapbox/streets-v12",
    "outdoors": "mapbox://styles/mapbox/outdoors-v12",
}


def _require_pydeck():
    """Raise a clear error when pydeck is missing."""
    if not PYDECK_AVAILABLE:
        raise ImportError(
            "pydeck is required for 3D map rendering.  "
            "Install it with:  pip install 'siege-utilities[3d]'"
        )


def _resolve_style(style: str) -> str:
    """Resolve a short style name to a Mapbox style URL."""
    return MAP_STYLES.get(style, style)


def _compute_view_state(
    lats: "pd.Series",
    lons: "pd.Series",
    *,
    pitch: float = 45.0,
    zoom: float = 10.0,
) -> "pdk.ViewState":
    """Auto-centre a ViewState over the data extent."""
    _require_pydeck()
    return pdk.ViewState(
        latitude=float(lats.mean()),
        longitude=float(lons.mean()),
        zoom=zoom,
        pitch=pitch,
        bearing=0,
    )


# ===================================================================
# ThreeDMapRenderer
# ===================================================================


class ThreeDMapRenderer:
    """High-level helper for creating pydeck 3D map visualisations.

    Parameters
    ----------
    mapbox_token : str | None
        Mapbox API key.  Falls back to the ``MAPBOX_ACCESS_TOKEN`` env-var
        that pydeck reads automatically when *None*.
    map_style : str
        One of ``"dark"``, ``"light"``, ``"satellite"``, ``"streets"``,
        ``"outdoors"`` **or** a full ``mapbox://`` URL.
    """

    def __init__(
        self,
        mapbox_token: Optional[str] = None,
        map_style: str = "dark",
    ):
        _require_pydeck()
        self.mapbox_token = mapbox_token
        self.map_style = _resolve_style(map_style)

    # ------------------------------------------------------------------
    # Layer builders
    # ------------------------------------------------------------------

    def create_hexagon_layer(
        self,
        df: "pd.DataFrame",
        lat_col: str = "latitude",
        lon_col: str = "longitude",
        value_col: Optional[str] = None,
        radius: int = 1000,
        elevation_scale: int = 100,
        color_range: Optional[List[List[int]]] = None,
        auto_highlight: bool = True,
        extruded: bool = True,
        coverage: float = 0.8,
        zoom: float = 10.0,
        pitch: float = 45.0,
    ) -> "pdk.Deck":
        """Create a 3D hexagonal-bin aggregation layer.

        Parameters
        ----------
        df : pandas.DataFrame
            Must contain *lat_col* and *lon_col* columns.
        value_col : str | None
            Column whose values are summed per hex.  When *None* the layer
            counts the number of points (default pydeck behaviour).
        radius : int
            Hexagon radius in metres.
        elevation_scale : int
            Multiplier applied to the aggregated elevation value.
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required")

        view = _compute_view_state(df[lat_col], df[lon_col], pitch=pitch, zoom=zoom)

        hex_layer_kwargs: Dict[str, Any] = dict(
            id="hex-layer",
            data=df,
            get_position=[lon_col, lat_col],
            radius=radius,
            elevation_scale=elevation_scale,
            elevation_range=[0, 1000],
            extruded=extruded,
            coverage=coverage,
            auto_highlight=auto_highlight,
            pickable=True,
        )
        if color_range is not None:
            hex_layer_kwargs["color_range"] = color_range

        layer = pdk.Layer("HexagonLayer", **hex_layer_kwargs)

        return pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            map_style=self.map_style,
            api_keys={"mapbox": self.mapbox_token} if self.mapbox_token else None,
        )

    def create_column_layer(
        self,
        df: "pd.DataFrame",
        lat_col: str = "latitude",
        lon_col: str = "longitude",
        value_col: str = "value",
        radius: int = 500,
        elevation_scale: int = 1,
        color: Optional[List[int]] = None,
        auto_highlight: bool = True,
        zoom: float = 10.0,
        pitch: float = 45.0,
    ) -> "pdk.Deck":
        """Create a 3D column layer at point locations.

        Each row produces a column whose height is proportional to
        *value_col* multiplied by *elevation_scale*.

        Parameters
        ----------
        color : list[int] | None
            RGBA colour list, e.g. ``[255, 140, 0, 200]``.
            Defaults to orange.
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required")

        view = _compute_view_state(df[lat_col], df[lon_col], pitch=pitch, zoom=zoom)

        if color is None:
            color = [255, 140, 0, 200]

        layer = pdk.Layer(
            "ColumnLayer",
            id="column-layer",
            data=df,
            get_position=[lon_col, lat_col],
            get_elevation=value_col,
            elevation_scale=elevation_scale,
            radius=radius,
            get_fill_color=color,
            auto_highlight=auto_highlight,
            pickable=True,
            extruded=True,
        )

        return pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            map_style=self.map_style,
            api_keys={"mapbox": self.mapbox_token} if self.mapbox_token else None,
        )

    def create_choropleth_3d(
        self,
        gdf: "gpd.GeoDataFrame",
        value_col: str = "value",
        elevation_scale: int = 100,
        fill_color: Optional[str] = None,
        line_color: Optional[List[int]] = None,
        opacity: float = 0.8,
        zoom: float = 10.0,
        pitch: float = 45.0,
    ) -> "pdk.Deck":
        """Create an extruded polygon (choropleth) layer from a GeoDataFrame.

        The polygons are extruded by *value_col* multiplied by
        *elevation_scale*, giving a 3D bar-on-map effect.

        Parameters
        ----------
        gdf : geopandas.GeoDataFrame
            Must have a ``geometry`` column of Polygon / MultiPolygon.
        fill_color : str | None
            A deck.gl JS expression for ``getFillColor``.  Defaults to an
            orange-to-red colour ramp based on *value_col*.
        """
        if not GEOPANDAS_AVAILABLE:
            raise ImportError("geopandas is required for create_choropleth_3d")

        # Convert GeoDataFrame to GeoJSON for pydeck
        geojson = json.loads(gdf.to_json())

        centroid = gdf.geometry.centroid
        view = pdk.ViewState(
            latitude=float(centroid.y.mean()),
            longitude=float(centroid.x.mean()),
            zoom=zoom,
            pitch=pitch,
            bearing=0,
        )

        if fill_color is None:
            # Simple ramp: low→orange, high→red
            fill_color = (
                f"[255, 255 - (properties.{value_col} / "
                f"{float(gdf[value_col].max()) or 1} * 200), 0, 200]"
            )

        if line_color is None:
            line_color = [255, 255, 255, 80]

        layer = pdk.Layer(
            "GeoJsonLayer",
            id="choropleth-3d",
            data=geojson,
            get_elevation=f"properties.{value_col}",
            elevation_scale=elevation_scale,
            extruded=True,
            filled=True,
            stroked=True,
            get_fill_color=fill_color,
            get_line_color=line_color,
            opacity=opacity,
            pickable=True,
            auto_highlight=True,
        )

        return pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            map_style=self.map_style,
            api_keys={"mapbox": self.mapbox_token} if self.mapbox_token else None,
        )

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def render_to_html(self, deck: "pdk.Deck", output_path: Union[str, Path]) -> Path:
        """Save a Deck to a standalone HTML file.

        Returns the resolved :class:`~pathlib.Path` of the written file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        deck.to_html(str(output_path), open_browser=False)
        log.info("3D map saved to %s", output_path)
        return output_path

    @staticmethod
    def render_in_notebook(deck: "pdk.Deck"):
        """Display the Deck in a Jupyter / Databricks notebook.

        Simply returns the *deck* object so that Jupyter's ``_repr_html_``
        protocol renders it inline.
        """
        return deck


# ===================================================================
# Module-level convenience functions
# ===================================================================


def create_3d_hexbin(
    df: "pd.DataFrame",
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    **kwargs,
) -> "pdk.Deck":
    """Convenience wrapper — create a hexagonal-bin 3D map.

    Accepts all keyword arguments supported by
    :meth:`ThreeDMapRenderer.create_hexagon_layer`.
    """
    renderer = ThreeDMapRenderer(
        mapbox_token=kwargs.pop("mapbox_token", None),
        map_style=kwargs.pop("map_style", "dark"),
    )
    return renderer.create_hexagon_layer(df, lat_col, lon_col, **kwargs)


def create_3d_columns(
    df: "pd.DataFrame",
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    value_col: str = "value",
    **kwargs,
) -> "pdk.Deck":
    """Convenience wrapper — create a column 3D map.

    Accepts all keyword arguments supported by
    :meth:`ThreeDMapRenderer.create_column_layer`.
    """
    renderer = ThreeDMapRenderer(
        mapbox_token=kwargs.pop("mapbox_token", None),
        map_style=kwargs.pop("map_style", "dark"),
    )
    return renderer.create_column_layer(df, lat_col, lon_col, value_col, **kwargs)
