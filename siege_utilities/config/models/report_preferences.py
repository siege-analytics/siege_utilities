"""
Report preferences model with comprehensive validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum


class PageOrientation(str, Enum):
    """Page orientation options."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class ReportFormat(str, Enum):
    """Report format options."""
    PDF = "pdf"
    PPTX = "pptx"
    HTML = "html"
    DOCX = "docx"


class ReportPreferences(BaseModel):
    """
    Report preferences with comprehensive validation.
    
    Provides type-safe, validated report generation settings with
    format constraints and layout validation.
    """
    
    # Basic preferences
    default_format: ReportFormat = Field(
        default=ReportFormat.PPTX,
        description="Default report format"
    )
    include_executive_summary: bool = Field(
        default=True,
        description="Include executive summary section"
    )
    chart_style: str = Field(
        default="professional",
        pattern=r'^(professional|minimal|colorful|monochrome|corporate)$',
        description="Chart style theme"
    )
    
    # Page layout
    page_size: str = Field(
        default="A4",
        pattern=r'^(A4|A3|Letter|Legal|Tabloid)$',
        description="Page size"
    )
    orientation: PageOrientation = Field(
        default=PageOrientation.LANDSCAPE,
        description="Page orientation"
    )
    
    # Content preferences
    include_table_of_contents: bool = Field(
        default=True,
        description="Include table of contents"
    )
    include_page_numbers: bool = Field(
        default=True,
        description="Include page numbers"
    )
    include_watermark: bool = Field(
        default=False,
        description="Include watermark"
    )
    watermark_text: Optional[str] = Field(
        None,
        max_length=50,
        description="Watermark text (if enabled)"
    )
    
    # Chart preferences
    chart_quality: str = Field(
        default="high",
        pattern=r'^(low|medium|high|ultra)$',
        description="Chart rendering quality"
    )
    chart_dpi: int = Field(
        default=300,
        ge=72,
        le=600,
        description="Chart DPI"
    )
    include_chart_titles: bool = Field(
        default=True,
        description="Include chart titles"
    )
    include_chart_legends: bool = Field(
        default=True,
        description="Include chart legends"
    )
    include_data_labels: bool = Field(
        default=False,
        description="Include data labels on charts"
    )
    
    # Section preferences
    sections: List[str] = Field(
        default_factory=lambda: ["executive_summary", "methodology", "findings", "recommendations"],
        description="Report sections to include"
    )
    
    # Export preferences
    export_metadata: bool = Field(
        default=True,
        description="Include metadata in export"
    )
    compress_output: bool = Field(
        default=False,
        description="Compress output files"
    )
    include_source_data: bool = Field(
        default=False,
        description="Include source data in export"
    )
    
    @field_validator('sections')
    @classmethod
    def validate_sections(cls, v):
        """Validate report sections."""
        valid_sections = {
            'executive_summary', 'methodology', 'findings', 'recommendations',
            'appendix', 'references', 'glossary', 'data_sources', 'limitations'
        }
        
        for section in v:
            if section not in valid_sections:
                raise ValueError(f'Invalid section: {section}. Valid sections: {valid_sections}')
        
        return v
    
    @field_validator('watermark_text')
    @classmethod
    def validate_watermark(cls, v, info):
        """Validate watermark settings."""
        include_watermark = info.data.get('include_watermark', False)
        
        if include_watermark and not v:
            raise ValueError('Watermark text is required when watermark is enabled')
        
        if v and len(v.strip()) == 0:
            raise ValueError('Watermark text cannot be empty')
        
        return v.strip() if v else None
    
    @field_validator('chart_dpi')
    @classmethod
    def validate_chart_dpi(cls, v, info):
        """Validate chart DPI based on quality setting."""
        quality = info.data.get('chart_quality', 'high')
        
        quality_dpi_map = {
            'low': 72,
            'medium': 150,
            'high': 300,
            'ultra': 600
        }
        
        recommended_dpi = quality_dpi_map.get(quality, 300)
        
        if v < recommended_dpi:
            # Could add warning here
            pass
        
        return v
    
    def get_export_settings(self) -> dict:
        """Get export settings as a dictionary."""
        return {
            'format': self.default_format.value,
            'page_size': self.page_size,
            'orientation': self.orientation.value,
            'include_metadata': self.export_metadata,
            'compress': self.compress_output,
            'include_source': self.include_source_data
        }
    
    def get_chart_settings(self) -> dict:
        """Get chart settings as a dictionary."""
        return {
            'style': self.chart_style,
            'quality': self.chart_quality,
            'dpi': self.chart_dpi,
            'include_titles': self.include_chart_titles,
            'include_legends': self.include_chart_legends,
            'include_labels': self.include_data_labels
        }
    
    def get_layout_settings(self) -> dict:
        """Get layout settings as a dictionary."""
        return {
            'page_size': self.page_size,
            'orientation': self.orientation.value,
            'include_toc': self.include_table_of_contents,
            'include_page_numbers': self.include_page_numbers,
            'include_watermark': self.include_watermark,
            'watermark_text': self.watermark_text
        }
    
    model_config = {
        "json_schema_serialization_mode": "json",
        "validate_assignment": True,
        "extra": "forbid"
    }
