"""
Extensible page type templates for PDF and PowerPoint reports.
Provides base templates and customization capabilities for different page types.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
import yaml
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)

@dataclass
class PageTemplate:
    """Base page template configuration."""
    
    name: str
    template_type: str  # 'pdf' or 'powerpoint'
    description: str = ""
    
    # Layout settings
    page_width: float = 8.5
    page_height: float = 11.0
    margins: Dict[str, float] = field(default_factory=lambda: {
        'top': 0.75, 'bottom': 0.75, 'left': 0.75, 'right': 0.75
    })
    
    # Content settings
    header_height: float = 0.5
    footer_height: float = 0.5
    content_margin: float = 0.25
    
    # Styling
    background_color: str = "#FFFFFF"
    header_background: str = "#F0F0F0"
    footer_background: str = "#F0F0F0"
    
    # Font settings
    default_font: str = "Helvetica"
    default_font_size: int = 11
    header_font: str = "Helvetica-Bold"
    header_font_size: int = 12
    
    # Custom elements
    custom_elements: Dict[str, Any] = field(default_factory=dict)
    
    # Template functions
    render_function: Optional[Callable] = None
    validation_function: Optional[Callable] = None

class PageTemplateManager:
    """
    Manages page templates for different report types.
    Provides extensible template system for PDF and PowerPoint.
    """
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the page template manager.
        
        Args:
            templates_dir: Directory containing template files
        """
        self.templates_dir = templates_dir or Path(__file__).parent / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        self.templates: Dict[str, PageTemplate] = {}
        self._load_default_templates()
        self._load_custom_templates()
    
    def _load_default_templates(self):
        """Load built-in default templates."""
        self.templates.update({
            # PDF Templates
            'pdf_title': PageTemplate(
                name='Title Page',
                template_type='pdf',
                description='Professional title page with branding',
                page_width=8.5,
                page_height=11.0,
                header_height=0.0,
                footer_height=0.0,
                custom_elements={
                    'title_position': 'center',
                    'subtitle_position': 'center',
                    'logo_position': 'top_center',
                    'author_position': 'bottom_left',
                    'date_position': 'bottom_right'
                }
            ),
            
            'pdf_executive_summary': PageTemplate(
                name='Executive Summary',
                template_type='pdf',
                description='Executive summary page with key insights',
                header_height=0.5,
                custom_elements={
                    'summary_boxes': True,
                    'key_metrics': True,
                    'action_items': True
                }
            ),
            
            'pdf_methodology': PageTemplate(
                name='Methodology',
                template_type='pdf',
                description='Methodology and technical approach page',
                custom_elements={
                    'process_flow': True,
                    'data_sources': True,
                    'assumptions': True
                }
            ),
            
            'pdf_findings': PageTemplate(
                name='Findings',
                template_type='pdf',
                description='Main findings and analysis page',
                custom_elements={
                    'chart_layout': 'grid',
                    'insight_boxes': True,
                    'data_tables': True
                }
            ),
            
            'pdf_recommendations': PageTemplate(
                name='Recommendations',
                template_type='pdf',
                description='Recommendations and next steps page',
                custom_elements={
                    'priority_levels': True,
                    'timeline': True,
                    'resource_requirements': True
                }
            ),
            
            'pdf_appendix': PageTemplate(
                name='Appendix',
                template_type='pdf',
                description='Supporting materials and data appendix',
                custom_elements={
                    'data_tables': True,
                    'technical_details': True,
                    'references': True
                }
            ),
            
            # PowerPoint Templates
            'ppt_title': PageTemplate(
                name='Title Slide',
                template_type='powerpoint',
                description='Professional title slide with branding',
                custom_elements={
                    'logo_position': 'top_right',
                    'subtitle_support': True,
                    'background_image': False
                }
            ),
            
            'ppt_toc': PageTemplate(
                name='Table of Contents',
                template_type='powerpoint',
                description='Navigation slide with agenda',
                custom_elements={
                    'section_links': True,
                    'progress_indicator': True,
                    'time_estimates': False
                }
            ),
            
            'ppt_content': PageTemplate(
                name='Content Slide',
                template_type='powerpoint',
                description='Standard content slide with title and body',
                custom_elements={
                    'bullet_points': True,
                    'image_support': True,
                    'chart_support': True
                }
            ),
            
            'ppt_chart': PageTemplate(
                name='Chart Slide',
                template_type='powerpoint',
                description='Slide optimized for charts and graphs',
                custom_elements={
                    'chart_emphasis': True,
                    'legend_position': 'bottom',
                    'data_source': True
                }
            ),
            
            'ppt_comparison': PageTemplate(
                name='Comparison Slide',
                template_type='powerpoint',
                description='Side-by-side comparison layout',
                custom_elements={
                    'two_column_layout': True,
                    'comparison_table': True,
                    'highlight_differences': True
                }
            ),
            
            'ppt_summary': PageTemplate(
                name='Summary Slide',
                template_type='powerpoint',
                description='Key takeaways and next steps',
                custom_elements={
                    'key_points': True,
                    'next_steps': True,
                    'contact_info': True
                }
            )
        })
    
    def _load_custom_templates(self):
        """Load custom templates from configuration files."""
        custom_templates_dir = self.templates_dir / "custom"
        custom_templates_dir.mkdir(exist_ok=True)
        
        for template_file in custom_templates_dir.glob("*.yaml"):
            try:
                with open(template_file, 'r') as f:
                    template_data = yaml.safe_load(f)
                    template = PageTemplate(**template_data)
                    self.templates[template.name] = template
                    log.info(f"Loaded custom template: {template.name}")
            except Exception as e:
                log.warning(f"Failed to load custom template {template_file}: {e}")
    
    def get_template(self, template_name: str) -> Optional[PageTemplate]:
        """
        Get a template by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            PageTemplate object or None if not found
        """
        return self.templates.get(template_name)
    
    def list_templates(self, template_type: Optional[str] = None) -> List[str]:
        """
        List available templates.
        
        Args:
            template_type: Filter by template type ('pdf' or 'powerpoint')
            
        Returns:
            List of template names
        """
        if template_type:
            return [name for name, template in self.templates.items() 
                   if template.template_type == template_type]
        return list(self.templates.keys())
    
    def create_custom_template(self, template: PageTemplate):
        """
        Create a custom template.
        
        Args:
            template: PageTemplate object to add
        """
        self.templates[template.name] = template
        self._save_custom_template(template)
    
    def _save_custom_template(self, template: PageTemplate):
        """Save custom template to file."""
        custom_templates_dir = self.templates_dir / "custom"
        custom_templates_dir.mkdir(exist_ok=True)
        
        template_file = custom_templates_dir / f"{template.name}.yaml"
        try:
            with open(template_file, 'w') as f:
                yaml.dump(template.__dict__, f, default_flow_style=False)
        except Exception as e:
            log.error(f"Failed to save custom template: {e}")
    
    def modify_template(self, template_name: str, **kwargs):
        """
        Modify an existing template.
        
        Args:
            template_name: Name of the template to modify
            **kwargs: Fields to modify
        """
        template = self.templates.get(template_name)
        if not template:
            log.warning(f"Template not found: {template_name}")
            return
        
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
            else:
                log.warning(f"Unknown template field: {key}")
        
        # Save if it's a custom template
        if template_name.startswith('custom_'):
            self._save_custom_template(template)
    
    def delete_template(self, template_name: str):
        """
        Delete a custom template.
        
        Args:
            template_name: Name of the template to delete
        """
        if template_name in self.templates:
            del self.templates[template_name]
            
            # Remove file if it's a custom template
            custom_templates_dir = self.templates_dir / "custom"
            template_file = custom_templates_dir / f"{template_name}.yaml"
            if template_file.exists():
                template_file.unlink()
                log.info(f"Deleted custom template: {template_name}")
    
    def export_template(self, template_name: str, output_path: str):
        """
        Export a template to a file.
        
        Args:
            template_name: Name of the template to export
            output_path: Path to export the template
        """
        template = self.templates.get(template_name)
        if not template:
            log.warning(f"Template not found: {template_name}")
            return
        
        try:
            with open(output_path, 'w') as f:
                yaml.dump(template.__dict__, f, default_flow_style=False)
            log.info(f"Exported template to: {output_path}")
        except Exception as e:
            log.error(f"Failed to export template: {e}")
    
    def import_template(self, input_path: str, template_name: Optional[str] = None):
        """
        Import a template from a file.
        
        Args:
            input_path: Path to import the template from
            template_name: Custom name for the imported template
        """
        try:
            with open(input_path, 'r') as f:
                template_data = yaml.safe_load(f)
            
            if template_name:
                template_data['name'] = template_name
            
            template = PageTemplate(**template_data)
            self.create_custom_template(template)
            log.info(f"Imported template: {template.name}")
        except Exception as e:
            log.error(f"Failed to import template: {e}")
    
    def get_template_preview(self, template_name: str) -> Dict[str, Any]:
        """
        Get a preview of template properties.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Dictionary with template preview information
        """
        template = self.templates.get(template_name)
        if not template:
            return {}
        
        return {
            'name': template.name,
            'type': template.template_type,
            'description': template.description,
            'dimensions': f"{template.page_width}\" x {template.page_height}\"",
            'margins': template.margins,
            'custom_elements': template.custom_elements
        }

# Global instance
template_manager = PageTemplateManager()

def get_template_manager() -> PageTemplateManager:
    """Get the global template manager."""
    return template_manager

def get_template(template_name: str) -> Optional[PageTemplate]:
    """Get a template by name."""
    return template_manager.get_template(template_name)
