"""Layout dispatcher for hex cartograms.

Resolves three input shapes into a uniform ``GeoDataFrame[geometry,
code, q, r]``:

* **Built-in name** (``"us_states"``, ``"us_cd_117"``, etc.) — looks up
  a registered canonical layout. v1 ships with no built-ins; the
  ``BUILTIN_LAYOUTS`` set is empty until ELE-2482 follow-up work bakes
  hand-positioned canonical layouts.
* **Algorithmic placement** — pass a GeoDataFrame of polygons; the
  module runs one of the algorithms in :mod:`.algorithms` to position
  them on a hex grid.
* **Hand-drawn mapping** — register a ``dict[code, (q, r)]`` via
  :func:`register_layout` and pass the registered name.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Union

from .algorithms import Algorithm, place_polygons
from .components import find_components, stitch_components
from .coords import AxialCoord, hexagon_polygon

if TYPE_CHECKING:  # pragma: no cover
    import geopandas as gpd

log = logging.getLogger(__name__)

__all__ = [
    "BUILTIN_LAYOUTS",
    "REGISTERED_LAYOUTS",
    "hex_tile_layout",
    "register_layout",
]


#: Set of layout names shipped with the package. Empty in v1; will grow
#: as canonical layouts (NPR-style US states, US CDs) are added in the
#: ELE-2482 follow-up.
BUILTIN_LAYOUTS: set[str] = set()

#: User-registered layouts, populated by :func:`register_layout`.
REGISTERED_LAYOUTS: dict[str, dict[str, AxialCoord]] = {}


def register_layout(name: str, mapping: dict[str, AxialCoord]) -> None:
    """Register a hand-positioned layout under *name*.

    The mapping must be ``{code: (q, r)}`` with no duplicate ``(q, r)``
    pairs. Use any reproducible code convention (``"AL"``, ``"01"``,
    ``"al-cd-7"``); :func:`hex_tile_layout` will join your data on
    whichever column you provide via ``code_col``.
    """
    if not name:
        raise ValueError("register_layout: name is required")
    seen_cells: set[AxialCoord] = set()
    for code, qr in mapping.items():
        if not isinstance(code, str):
            raise TypeError(
                f"register_layout({name!r}): codes must be str, got "
                f"{type(code).__name__}: {code!r}"
            )
        if qr in seen_cells:
            raise ValueError(
                f"register_layout({name!r}): duplicate hex {qr} for code {code!r}"
            )
        seen_cells.add(qr)
    REGISTERED_LAYOUTS[name] = dict(mapping)
    log.info("Registered layout %r with %d cells", name, len(mapping))


def hex_tile_layout(
    source: Union[str, "gpd.GeoDataFrame"],
    *,
    code_col: str = "code",
    algorithm: Union[Algorithm, str] = Algorithm.ANNEALING,
    components: Optional[Union[str, list[list[str]]]] = "auto",
    component_gap: int = 1,
    hex_size: float = 1.0,
    seed: Optional[int] = None,
) -> "gpd.GeoDataFrame":
    """Build a hex tile layout.

    Args:
        source: Either a registered/builtin layout name, or a
            GeoDataFrame of polygons to place algorithmically.
        code_col: Column name on the GeoDataFrame containing the
            polygon identifier (e.g. state abbreviation, FIPS code).
            Ignored when *source* is a string layout name.
        algorithm: One of :class:`Algorithm` (or its string value).
            Ignored when *source* is a registered layout name.
        components: ``"auto"`` (default) splits the input into
            connected components by polygon adjacency and lays each
            out independently with ``component_gap`` empty cells
            between them. ``"single"`` forces everything into one
            component. A pre-computed ``list[list[code]]`` lets the
            caller specify groups explicitly.
        component_gap: Number of empty hex cells between neighbouring
            components in the final output.
        hex_size: Cell circumradius in CRS units used for the output
            geometry. ``1.0`` is fine for visualization; choose a
            smaller value if you plan to overlay the cartogram on a
            real map.
        seed: Random seed for the annealing algorithm; ignored otherwise.

    Returns:
        ``GeoDataFrame[geometry, code, q, r]`` — one hexagon per
        polygon, with axial coords on each row for downstream tooling.
    """
    try:
        import geopandas as gpd  # noqa: F401  -- needed by _mapping_to_geodataframe
        from shapely.geometry import Polygon  # noqa: F401  -- ditto
    except ImportError as exc:
        raise ImportError(
            "hex_tile_layout requires geopandas + shapely. Install via "
            "'pip install siege-utilities[geo]'."
        ) from exc

    if isinstance(algorithm, str):
        algorithm = Algorithm(algorithm)

    if isinstance(source, str):
        mapping = _resolve_named_layout(source)
        return _mapping_to_geodataframe(mapping, hex_size=hex_size)

    # Algorithmic placement of a GeoDataFrame.
    if not hasattr(source, "geometry") or not hasattr(source, "iterrows"):
        raise TypeError(
            "hex_tile_layout: source must be a layout name or a "
            "GeoDataFrame; got " f"{type(source).__name__}"
        )
    if code_col not in source.columns:
        raise ValueError(
            f"hex_tile_layout: code_col={code_col!r} not in source.columns "
            f"({list(source.columns)})"
        )

    # Component splitting.
    if components == "single":
        comps = [[str(row[code_col]) for _, row in source.iterrows()]]
    elif components == "auto":
        comps = find_components(source, code_col)
    elif isinstance(components, list):
        comps = components
    else:
        raise ValueError(
            f"components must be 'auto', 'single', or a list of code-lists; "
            f"got {components!r}"
        )

    # Place each component independently.
    component_layouts: list[dict[str, AxialCoord]] = []
    for comp_codes in comps:
        comp_gdf = source[source[code_col].astype(str).isin(comp_codes)].copy()
        if comp_gdf.empty:
            continue
        layout = place_polygons(
            comp_gdf, code_col, algorithm=algorithm, seed=seed,
        )
        component_layouts.append(layout)

    final_mapping = stitch_components(
        component_layouts, component_gap=component_gap,
    )
    return _mapping_to_geodataframe(final_mapping, hex_size=hex_size)


def _resolve_named_layout(name: str) -> dict[str, AxialCoord]:
    """Look up a layout name in the user registry, then built-ins."""
    if name in REGISTERED_LAYOUTS:
        return REGISTERED_LAYOUTS[name]
    if name in BUILTIN_LAYOUTS:
        # Will be implemented in ELE-2482 follow-up; placeholder for now.
        raise NotImplementedError(
            f"Built-in layout {name!r} is reserved but not yet shipped. "
            "Until follow-up work lands, supply a hand-drawn layout via "
            "register_layout(name, mapping) or pass a GeoDataFrame for "
            "algorithmic placement."
        )
    available_registered = sorted(REGISTERED_LAYOUTS) or ["(none)"]
    raise KeyError(
        f"Unknown layout {name!r}. Registered: {available_registered}. "
        f"Built-in: {sorted(BUILTIN_LAYOUTS) or '(none)'}."
    )


def _mapping_to_geodataframe(
    mapping: dict[str, AxialCoord],
    *,
    hex_size: float,
) -> "gpd.GeoDataFrame":
    """Convert ``{code: (q, r)}`` to a GeoDataFrame with hex polygons."""
    import geopandas as gpd
    from shapely.geometry import Polygon

    rows = []
    for code, (q, r) in sorted(mapping.items()):
        verts = hexagon_polygon((q, r), size=hex_size)
        rows.append({
            "code": code,
            "q": q,
            "r": r,
            "geometry": Polygon(verts),
        })
    return gpd.GeoDataFrame(rows, geometry="geometry")
