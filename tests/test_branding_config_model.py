"""Tests for siege_utilities.config.models.branding_config module."""

import pytest
from pydantic import ValidationError
from siege_utilities.config.models.branding_config import BrandingConfig


def make_valid_config(**overrides):
    """Create a valid BrandingConfig with defaults, allowing overrides."""
    defaults = {
        "primary_color": "#1D365D",
        "secondary_color": "#4A90E2",
        "accent_color": "#FF6B35",
        "text_color": "#1A1A1A",
        "background_color": "#F6F6F6",
        "primary_font": "Helvetica",
        "secondary_font": "Arial",
    }
    defaults.update(overrides)
    return BrandingConfig(**defaults)


class TestBrandingConfigCreation:
    """Tests for BrandingConfig creation and defaults."""

    def test_valid_creation(self):
        config = make_valid_config()
        assert config.primary_color == "#1D365D"
        assert config.primary_font == "Helvetica"

    def test_default_layout_values(self):
        config = make_valid_config()
        assert config.header_height == 40
        assert config.footer_height == 20
        assert config.margin_top == 20

    def test_default_typography(self):
        config = make_valid_config()
        assert config.title_font_size == 24
        assert config.subtitle_font_size == 18
        assert config.body_font_size == 12
        assert config.caption_font_size == 10

    def test_default_chart_palette(self):
        config = make_valid_config()
        assert config.chart_color_palette == "viridis"


class TestBrandingConfigColorValidation:
    """Tests for color validation."""

    def test_invalid_hex_color_rejected(self):
        with pytest.raises(ValidationError):
            make_valid_config(primary_color="red")

    def test_short_hex_rejected(self):
        with pytest.raises(ValidationError):
            make_valid_config(primary_color="#FFF")

    def test_valid_hex_colors(self):
        config = make_valid_config(
            primary_color="#000000",
            secondary_color="#FFFFFF",
            accent_color="#aabbcc",
        )
        assert config.primary_color == "#000000"
        assert config.secondary_color == "#FFFFFF"
        assert config.accent_color == "#aabbcc"


class TestBrandingConfigFontValidation:
    """Tests for font validation."""

    def test_empty_font_rejected(self):
        with pytest.raises(ValidationError):
            make_valid_config(primary_font="")

    def test_font_with_special_chars_rejected(self):
        with pytest.raises(ValidationError):
            make_valid_config(primary_font="Font@Name!")

    def test_font_with_quotes_stripped(self):
        config = make_valid_config(primary_font="'Helvetica'")
        assert config.primary_font == "Helvetica"


class TestBrandingConfigLogoValidation:
    """Tests for logo validation."""

    def test_no_logo_is_valid(self):
        config = make_valid_config()
        assert config.logo_path is None

    def test_valid_logo_extension(self):
        config = make_valid_config(logo_path="/path/to/logo.png")
        assert config.logo_path is not None

    def test_invalid_logo_extension(self):
        with pytest.raises(ValidationError):
            make_valid_config(logo_path="/path/to/logo.txt")

    def test_logo_dimensions(self):
        config = make_valid_config(logo_width=100, logo_height=50)
        assert config.logo_width == 100
        assert config.logo_height == 50

    def test_logo_width_too_small(self):
        with pytest.raises(ValidationError):
            make_valid_config(logo_width=5)

    def test_logo_width_too_large(self):
        with pytest.raises(ValidationError):
            make_valid_config(logo_width=1000)


class TestBrandingConfigLayoutValidation:
    """Tests for layout validation."""

    def test_header_height_bounds(self):
        with pytest.raises(ValidationError):
            make_valid_config(header_height=10)  # below min 20
        with pytest.raises(ValidationError):
            make_valid_config(header_height=200)  # above max 100

    def test_margin_bounds(self):
        with pytest.raises(ValidationError):
            make_valid_config(margin_top=1)  # below min 5
        with pytest.raises(ValidationError):
            make_valid_config(margin_top=100)  # above max 50


class TestBrandingConfigChartValidation:
    """Tests for chart palette validation."""

    def test_valid_palette(self):
        for palette in ["viridis", "plasma", "Blues", "YlOrRd"]:
            config = make_valid_config(chart_color_palette=palette)
            assert config.chart_color_palette == palette

    def test_invalid_palette(self):
        with pytest.raises(ValidationError):
            make_valid_config(chart_color_palette="custom_palette")


class TestBrandingConfigMethods:
    """Tests for BrandingConfig helper methods."""

    def test_get_color_scheme(self):
        config = make_valid_config()
        scheme = config.get_color_scheme()
        assert "primary" in scheme
        assert "secondary" in scheme
        assert "accent" in scheme
        assert "text" in scheme
        assert "background" in scheme

    def test_get_typography_scheme(self):
        config = make_valid_config()
        scheme = config.get_typography_scheme()
        assert "primary_font" in scheme
        assert "title_size" in scheme
        assert "body_size" in scheme

    def test_get_layout_scheme(self):
        config = make_valid_config()
        scheme = config.get_layout_scheme()
        assert "header_height" in scheme
        assert "footer_height" in scheme
        assert "margin_top" in scheme

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            make_valid_config(unknown_field="value")
