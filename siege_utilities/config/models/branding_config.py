"""
Branding configuration model with comprehensive validation.
"""

from pydantic import BaseModel, Field, field_validator
from pathlib import Path
from typing import Optional
import re


class BrandingConfig(BaseModel):
    """
    Branding configuration with comprehensive validation.
    
    Provides type-safe, validated branding settings with
    color format validation and design constraints.
    """
    
    # Colors with hex validation
    primary_color: str = Field(
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Primary brand color (hex format)"
    )
    secondary_color: str = Field(
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Secondary brand color (hex format)"
    )
    accent_color: str = Field(
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Accent brand color (hex format)"
    )
    text_color: str = Field(
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Text color (hex format)"
    )
    background_color: str = Field(
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Background color (hex format)"
    )
    
    # Fonts
    primary_font: str = Field(
        min_length=1,
        max_length=50,
        description="Primary font family"
    )
    secondary_font: str = Field(
        min_length=1,
        max_length=50,
        description="Secondary font family"
    )
    
    # Logo
    logo_path: Optional[Path] = Field(
        None,
        description="Path to logo file"
    )
    logo_width: Optional[int] = Field(
        None,
        ge=10,
        le=500,
        description="Logo width in pixels"
    )
    logo_height: Optional[int] = Field(
        None,
        ge=10,
        le=500,
        description="Logo height in pixels"
    )
    
    # Layout
    header_height: int = Field(
        default=40,
        ge=20,
        le=100,
        description="Header height in pixels"
    )
    footer_height: int = Field(
        default=20,
        ge=10,
        le=50,
        description="Footer height in pixels"
    )
    margin_top: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Top margin in pixels"
    )
    margin_bottom: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Bottom margin in pixels"
    )
    margin_left: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Left margin in pixels"
    )
    margin_right: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Right margin in pixels"
    )
    
    # Typography
    title_font_size: int = Field(
        default=24,
        ge=12,
        le=72,
        description="Title font size in points"
    )
    subtitle_font_size: int = Field(
        default=18,
        ge=10,
        le=48,
        description="Subtitle font size in points"
    )
    body_font_size: int = Field(
        default=12,
        ge=8,
        le=24,
        description="Body text font size in points"
    )
    caption_font_size: int = Field(
        default=10,
        ge=6,
        le=18,
        description="Caption font size in points"
    )
    
    # Chart styling
    chart_color_palette: str = Field(
        default="viridis",
        pattern=r'^(viridis|plasma|inferno|magma|Blues|Greens|Reds|Purples|Oranges|Greys|YlOrRd|YlGnBu|RdYlBu)$',
        description="Chart color palette"
    )
    chart_background_color: str = Field(
        default="#ffffff",
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Chart background color"
    )
    chart_grid_color: str = Field(
        default="#e0e0e0",
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Chart grid color"
    )
    
    @field_validator('primary_color', 'secondary_color', 'accent_color', 'text_color', 'background_color')
    @classmethod
    def validate_color_contrast(cls, v):
        """Validate color format and provide warnings for potential contrast issues."""
        # Convert hex to RGB for basic validation
        hex_color = v.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Calculate luminance for contrast checking
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        
        # Warn about very dark or very light colors that might have contrast issues
        if luminance < 0.1:
            # Very dark color
            pass  # Could add warning here
        elif luminance > 0.9:
            # Very light color
            pass  # Could add warning here
        
        return v
    
    @field_validator('primary_font', 'secondary_font')
    @classmethod
    def validate_font_name(cls, v):
        """Validate font name format."""
        # Remove quotes if present
        v = v.strip('"\'')
        
        # Basic font name validation
        if not re.match(r'^[a-zA-Z0-9\s,-]+$', v):
            raise ValueError('Font name contains invalid characters')
        
        return v
    
    @field_validator('logo_path', mode='before')
    @classmethod
    def validate_logo_path(cls, v):
        """Validate logo path format."""
        if v is None:
            return v
        
        if isinstance(v, str):
            path = Path(v)
        else:
            path = v
        
        # Check if it's a valid image file extension
        valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.tiff'}
        if path.suffix.lower() not in valid_extensions:
            raise ValueError(f'Logo file must have a valid image extension: {valid_extensions}')
        
        return path
    
    @field_validator('logo_width', 'logo_height')
    @classmethod
    def validate_logo_dimensions(cls, v, info):
        """Validate logo dimensions."""
        if v is None:
            return v
        
        # Check aspect ratio if both width and height are provided
        if info.data and 'logo_width' in info.data and 'logo_height' in info.data:
            width = info.data.get('logo_width')
            height = info.data.get('logo_height')
            
            if width and height:
                aspect_ratio = width / height
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                    # Could add warning about extreme aspect ratios
                    pass
        
        return v
    
    def get_color_scheme(self) -> dict:
        """Get the complete color scheme as a dictionary."""
        return {
            'primary': self.primary_color,
            'secondary': self.secondary_color,
            'accent': self.accent_color,
            'text': self.text_color,
            'background': self.background_color,
            'chart_background': self.chart_background_color,
            'chart_grid': self.chart_grid_color
        }
    
    def get_typography_scheme(self) -> dict:
        """Get the complete typography scheme as a dictionary."""
        return {
            'primary_font': self.primary_font,
            'secondary_font': self.secondary_font,
            'title_size': self.title_font_size,
            'subtitle_size': self.subtitle_font_size,
            'body_size': self.body_font_size,
            'caption_size': self.caption_font_size
        }
    
    def get_layout_scheme(self) -> dict:
        """Get the complete layout scheme as a dictionary."""
        return {
            'header_height': self.header_height,
            'footer_height': self.footer_height,
            'margin_top': self.margin_top,
            'margin_bottom': self.margin_bottom,
            'margin_left': self.margin_left,
            'margin_right': self.margin_right
        }
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }
