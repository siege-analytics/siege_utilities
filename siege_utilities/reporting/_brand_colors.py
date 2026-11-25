"""Check branding configs, read their colours the way the charts do, pick text colours.

Charts hand ``branding_config['colors']`` values straight to matplotlib, so
the PDF side parses them with matplotlib too. Tables and the page template
then draw the same colour as the chart for every form matplotlib accepts:
names, ``tab:``/``C0`` names, short and alpha hex, and RGB(A) tuples. The
``"0x13293D"`` strings and integers that ReportLab's ``HexColor`` read for
template YAML through 6.0.0 are still accepted.
"""

import math
from numbers import Real
from typing import Any, Sequence

from .client_branding import BrandingColorError, BrandingConfigError

try:
    from matplotlib.colors import to_rgba
except ImportError:  # matplotlib is optional; fall back to ReportLab's parser.
    to_rgba = None

try:
    from reportlab.lib.colors import Color, HexColor, toColor
except ImportError:  # ReportLab is optional until a PDF is built.
    Color = None
    HexColor = None
    toColor = None

#: WCAG 2.x AA contrast ratio for normal-size text.
AA_TEXT_CONTRAST = 4.5
#: WCAG 2.x AA contrast ratio for graphical objects such as table rules.
AA_GRAPHIC_CONTRAST = 3.0
#: The ``colors`` keys the charts, tables and page template read.
BRAND_COLOR_KEYS = ("primary", "secondary", "accent", "text_color", "header_footer_text_color")
#: The ``colors`` keys the charts hand to matplotlib, which has no ``0x`` form.
CHART_COLOR_KEYS = ("primary", "secondary", "accent")
#: Branding sections that must be mappings when present.
BRANDING_SECTIONS = ("fonts", "header", "footer", "logo", "footer_logo", "page_margins")


def _colour_error(value: Any, key: str) -> BrandingColorError:
    return BrandingColorError(
        f"branding colors.{key}={value!r} is not a colour: use a name ('navy'), hex "
        f"('#13293D', '#abc', '#13293D80', '0x13293D'), an RGB integer or an RGB(A) "
        f"tuple of floats in 0-1"
    )


def _is_hex_integer_form(value: Any) -> bool:
    """The ``0x...`` strings and integers ReportLab's ``HexColor`` reads."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, str) and value.strip().lower().startswith("0x")


def _rgba(value: Any, key: str) -> tuple[float, float, float, float]:
    """Parse a colour to RGBA floats, as the chart side does when it can."""
    if value is None or isinstance(value, bool):
        raise _colour_error(value, key)
    try:
        if _is_hex_integer_form(value) and HexColor is not None:
            number = value if isinstance(value, int) else int(value.strip(), 16)
            if not 0 <= number <= 0xFFFFFF:
                raise ValueError(f"{value!r} is outside 0x000000-0xFFFFFF")
            return tuple(HexColor(number).rgba())
        if to_rgba is not None:
            return tuple(to_rgba(value))
        if toColor is not None:
            return tuple(toColor(value).rgba())
    except (ValueError, TypeError) as exc:
        raise _colour_error(value, key) from exc
    raise ImportError(
        "matplotlib or ReportLab is required to read branding colours. "
        "Install with: pip install 'siege-utilities[reporting]'"
    )


def validate_brand_colors(branding_config: dict) -> None:
    """Check the ``colors`` entries the reports read, before anything draws.

    Only ``BRAND_COLOR_KEYS`` are checked; other keys are left alone. A key
    that is present must hold a colour (``None`` is not one). Without
    matplotlib and ReportLab nothing can draw, so nothing is checked.

    Raises:
        BrandingColorError: If ``colors`` is not a mapping or a read entry
            is not a colour.
    """
    if to_rgba is None and toColor is None:
        return
    colours = branding_config.get("colors")
    if colours is None:
        return
    if not isinstance(colours, dict):
        raise BrandingColorError(
            f"branding colors must be a mapping of names to colours, got {colours!r}"
        )
    for key in BRAND_COLOR_KEYS:
        if key not in colours:
            continue
        if key in CHART_COLOR_KEYS and _is_hex_integer_form(colours[key]):
            raise BrandingColorError(
                f"branding colors.{key}={colours[key]!r}: charts cannot read '0x' or integer "
                f"colours; write it as hex, e.g. '#13293D'"
            )
        _rgba(colours[key], key)


def _section(branding_config: dict, name: str) -> dict:
    value = branding_config.get(name)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise BrandingConfigError(f"branding {name} must be a mapping, got {value!r}")
    return value


def _check_number(value: Any, name: str, minimum: float = 0.0) -> None:
    if value is None:
        return
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not math.isfinite(value) or value < minimum):
        raise BrandingConfigError(
            f"branding {name} must be a finite number of at least {minimum:g}, got {value!r}"
        )


def _check_text(value: Any, name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise BrandingConfigError(f"branding {name} must be text, got {value!r}")


def validate_branding_layout(branding_config: dict) -> None:
    """Check the page-layout entries the template reads, naming any bad one.

    ``fonts``, ``header``, ``footer``, ``logo``, ``footer_logo`` and
    ``page_margins`` must be mappings when present (``None`` means unset);
    font sizes, logo sizes and margins must be non-negative numbers; texts
    and the logo ``image_url`` must be strings; and
    ``footer.page_number_format`` must take exactly one ``%`` value, such as
    ``'Page %s'``.

    Raises:
        BrandingConfigError: If an entry has the wrong shape.
    """
    sections = {name: _section(branding_config, name) for name in BRANDING_SECTIONS}
    fonts = sections["fonts"]
    _check_text(fonts.get("default_font"), "fonts.default_font")
    for style in ("h1", "h2", "h3", "BodyText"):
        entry = fonts.get(style)
        if entry is None:
            continue
        if not isinstance(entry, dict):
            raise BrandingConfigError(f"branding fonts.{style} must be a mapping, got {entry!r}")
        for metric in ("font_size", "leading"):
            _check_number(entry.get(metric), f"fonts.{style}.{metric}", minimum=1.0)
    for name in ("header", "footer"):
        for side in ("left_text", "right_text"):
            _check_text(sections[name].get(side), f"{name}.{side}")
    footer = sections["footer"]
    if "page_number_format" in footer:
        page_format = footer["page_number_format"]
        _check_text(page_format, "footer.page_number_format")
        try:
            page_format % 1
        except (TypeError, ValueError) as exc:
            raise BrandingConfigError(
                f"branding footer.page_number_format={page_format!r} must take exactly one "
                f"%-style value, such as 'Page %s'"
            ) from exc
    for name in ("logo", "footer_logo"):
        _check_text(sections[name].get("image_url"), f"{name}.image_url")
        for size in ("width", "height"):
            _check_number(sections[name].get(size), f"{name}.{size}")
    for side in ("top", "bottom", "left", "right"):
        _check_number(sections["page_margins"].get(side), f"page_margins.{side}")


def brand_color(value: Any, key: str) -> "Color":
    """Return a ReportLab colour for one ``branding_config['colors']`` entry.

    Args:
        value: The colour as given in the branding config.
        key: The ``colors`` key, used in the error message.

    Returns:
        A ``reportlab.lib.colors.Color``, keeping any alpha.

    Raises:
        ImportError: If ReportLab is not installed.
        BrandingColorError: If the value is not a colour.
    """
    if Color is None:
        raise ImportError(
            "ReportLab is required to apply branding colours. "
            "Install with: pip install reportlab"
        )
    red, green, blue, alpha = _rgba(value, key)
    return Color(red, green, blue, alpha=alpha)


def _on_white(colour: "Color") -> tuple[float, float, float]:
    """Composite a possibly translucent colour over a white page."""
    alpha = colour.alpha if colour.alpha is not None else 1.0
    return tuple(alpha * part + (1.0 - alpha) for part in colour.rgb())


def relative_luminance(colour: "Color") -> float:
    """WCAG relative luminance of a colour drawn on a white page."""
    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    red, green, blue = (channel(part) for part in _on_white(colour))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: "Color", second: "Color") -> float:
    """WCAG contrast ratio between two colours, from 1 to 21."""
    high, low = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def readable_text_color(background: "Color", preferred: Sequence["Color"],
                        fallback: Sequence["Color"]) -> "Color":
    """Pick a text colour that is readable on *background*.

    The first *preferred* colour meeting WCAG AA (4.5:1) wins, so a brand's
    usual text colour is kept whenever it is readable. Otherwise the colour
    with the highest contrast among *preferred* and *fallback* is used.
    """
    for colour in preferred:
        if contrast_ratio(background, colour) >= AA_TEXT_CONTRAST:
            return colour
    candidates = list(preferred) + list(fallback)
    return max(candidates, key=lambda colour: contrast_ratio(background, colour))
