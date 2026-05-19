"""Hex cartogram (tile-map) construction and rendering.

A hex cartogram replaces each administrative unit (state, congressional
district, county, country) with a single hexagon, positioned to roughly
preserve geography. The whole point: small jurisdictions get the same
visual weight as large ones, so Wyoming and DC don't get drowned out by
California.

Public API (re-exported from this package):

* :func:`hex_tile_layout` — build a layout (GeoDataFrame[geometry, code,
  q, r]) from either a built-in name, an algorithmic placement of a
  GeoDataFrame, or a hand-drawn mapping registered via
  :func:`register_layout`.
* :func:`hex_tile_map` — matplotlib renderer that takes a values series
  + a layout and returns a Figure. Three sizing modes (equal,
  value_proportional, value_sqrt) per the design discussion.
* :func:`register_layout` — extension hook for user-supplied
  hand-positioned layouts.
* :data:`BUILTIN_LAYOUTS` — set of layout names shipped with the
  package. Empty in v1; populated as we add canonical layouts in
  follow-up work.
* :class:`Algorithm` enum — placement-algorithm choices: ``greedy``,
  ``hungarian``, ``annealing``. (``force_directed`` and ``ilp`` are
  future work; see ELE-2482.)
* :class:`Sizing` enum — sizing modes: ``equal``, ``value_proportional``,
  ``value_sqrt``.

See ``docs/source/hex_cartograms.md`` for the algorithm comparison and
worked examples.
"""

from .algorithms import Algorithm
from .layouts import BUILTIN_LAYOUTS, hex_tile_layout, register_layout
from .renderer import Sizing, hex_tile_map

__all__ = [
    "Algorithm",
    "BUILTIN_LAYOUTS",
    "Sizing",
    "hex_tile_layout",
    "hex_tile_map",
    "register_layout",
]
