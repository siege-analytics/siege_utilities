"""Decimal formatting for legend range labels (#1535).

Legend ranges must not misstate where the data lies. Choosing decimals from
the interval width alone loses fractional offsets: 0.004 to 0.054 in five
steps of 0.01 printed as ``0.00 - 0.01 ... 0.04 - 0.05`` and left out the
maximum. The helpers here choose decimals from the edges themselves as well
as the widths, and never let the outermost displayed bounds exclude the
data they describe.
"""

from __future__ import annotations

import math
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import List, Optional, Sequence

# Interpolated or evenly divided edges (1/3, 100/7) never terminate. Past
# this many decimals the label shows the edge rounded, and only the outer
# bounds are pushed outward so they still contain the data.
MAX_EXTRA_DECIMALS = 6


def _round_trips(edge: float, decimals: int) -> bool:
    """True when the edge, written with ``decimals`` places, reads back as the same float.

    This is the test for "shown exactly", with no tolerance: 1e12 plus 36
    units in the last place needs four decimals (``...000.0044``) to read
    back, and three (``...000.004``) do not. Non-finite edges are never
    checked.
    """
    edge = float(edge)
    return not math.isfinite(edge) or float(f"{edge:.{decimals}f}") == edge


def _shown_value(edge: float, decimals: int, rounding: Optional[str]) -> float:
    """The value a label with ``decimals`` places shows for the edge.

    Interior edges (``rounding`` None) are rounded to nearest. Outer edges
    that do not round-trip are rounded outward from the float's exact binary
    value (``Decimal(edge)``), so the bound is never on the wrong side.
    """
    if rounding is None or _round_trips(edge, decimals):
        return float(f"{edge:.{decimals}f}")
    return float(Decimal(edge).quantize(Decimal(1).scaleb(-decimals), rounding=rounding))


def _required_decimals(edge: float, minimum: int, cap: int, rounding: Optional[str]) -> int:
    """Fewest decimals, from ``minimum`` up to ``cap``, that one edge needs.

    If the edge reads back exactly at some count up to the cap, it needs that
    count: 1000000000.100001 needs six, and no shorter label may stand for it.
    If it never reads back within the cap (1/3, or a pandas edge such as
    1000.0000000000002), it is shown as its value at the cap, and needs only
    as many decimals as give that same value: 1000.0000000000002 shows as
    ``1000.0`` because ``1000.0`` and ``1000.000000`` are the same number. An
    outer edge is compared by its outward-rounded value, so a last edge of
    1000.0000000000002 still needs the cap (``1000.000001``) rather than being
    widened to ``1000.1``.
    """
    edge = float(edge)
    if not math.isfinite(edge):
        return minimum
    for decimals in range(minimum, cap + 1):
        if _round_trips(edge, decimals):
            return decimals
    at_cap = _shown_value(edge, cap, rounding)
    for decimals in range(minimum, cap + 1):
        if _shown_value(edge, decimals, rounding) == at_cap:
            return decimals
    return cap


def _rounding_for(index: int, count: int) -> Optional[str]:
    if index == 0:
        return ROUND_FLOOR
    if index == count - 1:
        return ROUND_CEILING
    return None


def range_label_decimals(edges: Sequence[float], minimum_decimals: int) -> int:
    """Decimals for a legend: the most any single edge needs, capped.

    ``minimum_decimals`` is the caller's width-based precision, and the cap is
    ``max(minimum_decimals, MAX_EXTRA_DECIMALS)``. Each edge's need is set by
    :func:`_required_decimals`.
    """
    cap = max(minimum_decimals, MAX_EXTRA_DECIMALS)
    count = len(edges)
    return max(
        (_required_decimals(edge, minimum_decimals, cap, _rounding_for(i, count))
         for i, edge in enumerate(edges)),
        default=minimum_decimals,
    )


def format_range_edges(edges: Sequence[float], minimum_decimals: int) -> List[str]:
    """Format bin edges for contiguous legend ranges that contain the data, within the six-decimal cap.

    Every edge uses the same number of decimals (see
    :func:`range_label_decimals`), so an edge that can be written exactly
    within the cap is written exactly. Adjacent ranges share one formatted
    string for their common edge. An edge that cannot be written exactly within
    the cap is shown as its value at the cap. When that edge is the first or
    last, it is rounded outward from its exact binary value (down for the
    first, up for the last), so the displayed extent always contains the
    edges; a displayed outer bound can then be slightly wider than the data:
    0.0000013 to 0.0000113 shows as 0.000001 to 0.000012. Interior edges are
    rounded to nearest and are never widened, so a value closer to an interior
    edge than the cap's last place can sit on the printed edge rather than
    inside its own range (an edge of -4.16e-17 prints as 0.00). An edge shown
    as zero carries no sign.
    """
    decimals = range_label_decimals(edges, minimum_decimals)
    quantum = Decimal(1).scaleb(-decimals)

    def text(edge: float, rounding: Optional[str]) -> str:
        edge = float(edge)
        if rounding is not None and math.isfinite(edge) and not _round_trips(edge, decimals):
            outward = Decimal(edge).quantize(quantum, rounding=rounding)
            if outward == 0:
                # Rounding -1e-17 up gives Decimal("-0.000000"); show it unsigned.
                outward = abs(outward)
            return f"{outward:,.{decimals}f}"
        if math.isfinite(edge) and round(edge, decimals) == 0:
            # A tiny edge shown as zero carries no sign: "0.000", not "-0.000".
            return f"{0.0:,.{decimals}f}"
        return f"{edge:,.{decimals}f}"

    count = len(edges)
    return [text(edge, _rounding_for(i, count)) for i, edge in enumerate(edges)]
