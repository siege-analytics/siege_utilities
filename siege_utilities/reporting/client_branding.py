"""
Client branding management for siege_utilities reporting system.
Handles client-specific configurations, logos, colors, and styling.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import shutil

log = logging.getLogger(__name__)

class ClientBrandingManager:
    """
    Manages client branding configurations for reports.
    Handles logos, colors, fonts, and styling preferences.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the branding manager.
        
        Args:
            config_dir: Directory containing branding configuration files
        """
        self.config_dir = config_dir or Path.home() / ".siege_utilities" / "branding"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._load_branding_templates()

    def _load_branding_templates(self):
        """Load predefined branding templates."""
        self.branding_templates = {
            'siege_analytics': {
                'name': 'Siege Analytics',
                'colors': {
                    'primary': '#1D365D',
                    'secondary': '#4A90E2',
                    'accent': '#FF6B35',
                    'text_color': '#1A1A1A',
                    'header_footer_text_color': '#666666',
                    'background': '#F6F6F6'
                },
                'fonts': {
                    'default_font': 'Helvetica',
                    'h1': {'font_size': 24, 'leading': 28},
                    'h2': {'font_size': 18, 'leading': 22},
                    'h3': {'font_size': 16, 'leading': 20},
                    'BodyText': {'font_size': 11, 'leading': 14}
                },
                'logo': {
                    'image_url': 'https://siegeanalytics.com/logo.png',
                    'width': 1.5,
                    'height': 0.6
                },
                'header': {
                    'left_text': 'Siege Analytics Report',
                    'right_text': 'Professional Analytics Solutions'
                },
                'footer': {
                    'left_text': 'Prepared by: Siege Analytics',
                    'right_text': 'www.siegeanalytics.com',
                    'page_number_format': 'Page %s'
                },
                'page_margins': {
                    'top': 1.0,
                    'bottom': 1.0,
                    'left': 0.75,
                    'right': 0.75
                }
            },
            'masai_interactive': {
                'name': 'Masai Interactive',
                'colors': {
                    'primary': '#0077CC',
                    'secondary': '#EEEEEE',
                    'accent': '#FF6B35',
                    'text_color': '#333333',
                    'header_footer_text_color': '#666666',
                    'background': '#FFFFFF'
                },
                'fonts': {
                    'default_font': 'Liberation-Serif',
                    'h1': {'font_size': 24, 'leading': 28},
                    'h2': {'font_size': 18, 'leading': 22},
                    'h3': {'font_size': 14, 'leading': 18},
                    'BodyText': {'font_size': 12, 'leading': 14}
                },
                'logo': {
                    'image_url': 'https://masaiinteractive.com/wp-content/uploads/2023/02/Masai-Logo-2023.png',
                    'width': 1.5,
                    'height': 0.6
                },
                'footer_logo': {
                    'image_url': 'https://masaiinteractive.com/wp-content/uploads/2024/02/cropped-Masai-Logo-Abbreviated4.png',
                    'width': 0.5,
                    'height': 0.2
                },
                'header': {
                    'left_text': 'Masai Interactive Report',
                    'right_text': 'Creative Digital Solutions'
                },
                'footer': {
                    'left_text': 'Prepared by: Masai Interactive',
                    'right_text': 'www.masaiinteractive.com',
                    'page_number_format': 'Page %s'
                },
                'page_margins': {
                    'top': 1.0,
                    'bottom': 1.0,
                    'left': 1.0,
                    'right': 1.0
                }
            }
        }

    def create_client_branding(self, client_name: str, branding_config: Dict[str, Any]) -> Path:
        """
        Create a new client branding configuration.
        
        Args:
            client_name: Name of the client
            branding_config: Branding configuration dictionary
            
        Returns:
            Path to the created configuration file
        """
        try:
            # Validate required fields
            required_fields = ['name', 'colors', 'fonts']
            for field in required_fields:
                if field not in branding_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create client directory
            client_dir = self.config_dir / client_name.lower().replace(' ', '_')
            client_dir.mkdir(exist_ok=True)
            
            # Create branding config file
            config_file = client_dir / f"{client_name.lower().replace(' ', '_')}_branding.yaml"
            
            with open(config_file, 'w') as f:
                yaml.dump(branding_config, f, default_flow_style=False, indent=2)
            
            log.info(f"Created branding configuration for {client_name}: {config_file}")
            return config_file
            
        except Exception as e:
            log.error(f"Error creating branding configuration for {client_name}: {e}")
            raise

    def get_client_branding(self, client_name: str) -> Optional[Dict[str, Any]]:
        """
        Get branding configuration for a specific client.
        
        Args:
            client_name: Name of the client
            
        Returns:
            Branding configuration dictionary or None if not found
        """
        try:
            # First check predefined templates
            if client_name.lower() in self.branding_templates:
                return self.branding_templates[client_name.lower()]
            
            # Check for custom client configurations
            client_dir = self.config_dir / client_name.lower().replace(' ', '_')
            if client_dir.exists():
                # Look for branding config files
                for config_file in client_dir.glob("*_branding.yaml"):
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)
                        log.info(f"Loaded branding configuration from {config_file}")
                        return config
            
            log.warning(f"No branding configuration found for client: {client_name}")
            return None
            
        except Exception as e:
            log.error(f"Error loading branding configuration for {client_name}: {e}")
            return None

    def update_client_branding(self, client_name: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing client branding configuration.
        
        Args:
            client_name: Name of the client
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        try:
            current_config = self.get_client_branding(client_name)
            if not current_config:
                log.warning(f"No existing branding configuration found for {client_name}")
                return False
            
            # Apply updates
            for key, value in updates.items():
                if isinstance(value, dict) and key in current_config:
                    current_config[key].update(value)
                else:
                    current_config[key] = value
            
            # Save updated configuration
            client_dir = self.config_dir / client_name.lower().replace(' ', '_')
            config_file = client_dir / f"{client_name.lower().replace(' ', '_')}_branding.yaml"
            
            with open(config_file, 'w') as f:
                yaml.dump(current_config, f, default_flow_style=False, indent=2)
            
            log.info(f"Updated branding configuration for {client_name}")
            return True
            
        except Exception as e:
            log.error(f"Error updating branding configuration for {client_name}: {e}")
            return False

    def list_clients(self) -> List[str]:
        """
        List all available client branding configurations.
        
        Returns:
            List of client names
        """
        clients = list(self.branding_templates.keys())
        
        # Add custom clients
        if self.config_dir.exists():
            for client_dir in self.config_dir.iterdir():
                if client_dir.is_dir():
                    client_name = client_dir.name.replace('_', ' ').title()
                    if client_name not in clients:
                        clients.append(client_name)
        
        return sorted(clients)

    def delete_client_branding(self, client_name: str) -> bool:
        """
        Delete a client branding configuration.
        
        Args:
            client_name: Name of the client to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Cannot delete predefined templates
            if client_name.lower() in self.branding_templates:
                log.warning(f"Cannot delete predefined template: {client_name}")
                return False
            
            client_dir = self.config_dir / client_name.lower().replace(' ', '_')
            if client_dir.exists():
                shutil.rmtree(client_dir)
                log.info(f"Deleted branding configuration for {client_name}")
                return True
            else:
                log.warning(f"No branding configuration found for {client_name}")
                return False
                
        except Exception as e:
            log.error(f"Error deleting branding configuration for {client_name}: {e}")
            return False

    def create_branding_from_template(self, client_name: str, template_name: str, 
                                    customizations: Optional[Dict[str, Any]] = None) -> Path:
        """
        Create client branding from a predefined template.
        
        Args:
            client_name: Name of the new client
            template_name: Name of the template to use
            customizations: Optional customizations to apply
            
        Returns:
            Path to the created configuration file
        """
        try:
            if template_name not in self.branding_templates:
                raise ValueError(f"Template '{template_name}' not found")
            
            # Copy template
            branding_config = self.branding_templates[template_name].copy()
            branding_config['name'] = client_name
            
            # Apply customizations
            if customizations:
                for key, value in customizations.items():
                    if isinstance(value, dict) and key in branding_config:
                        branding_config[key].update(value)
                    else:
                        branding_config[key] = value
            
            return self.create_client_branding(client_name, branding_config)
            
        except Exception as e:
            log.error(f"Error creating branding from template: {e}")
            raise

    def validate_branding_config(self, branding_config: Dict[str, Any]) -> List[str]:
        """
        Validate a branding configuration.
        
        Args:
            branding_config: Branding configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        required_fields = ['name', 'colors', 'fonts']
        for field in required_fields:
            if field not in branding_config:
                errors.append(f"Missing required field: {field}")
        
        # Check colors
        if 'colors' in branding_config:
            required_colors = ['primary', 'text_color']
            for color in required_colors:
                if color not in branding_config['colors']:
                    errors.append(f"Missing required color: {color}")
        
        # Check fonts
        if 'fonts' in branding_config:
            required_fonts = ['default_font']
            for font in required_fonts:
                if font not in branding_config['fonts']:
                    errors.append(f"Missing required font: {font}")
        
        # Check logo configuration
        if 'logo' in branding_config:
            logo_config = branding_config['logo']
            if 'image_url' not in logo_config:
                errors.append("Logo configuration missing image_url")
        
        return errors

    def export_branding_config(self, client_name: str, export_path: Path) -> bool:
        """
        Export a client branding configuration to a file.
        
        Args:
            client_name: Name of the client
            export_path: Path where to export the configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            branding_config = self.get_client_branding(client_name)
            if not branding_config:
                return False
            
            # Export as YAML
            if export_path.suffix.lower() in ['.yaml', '.yml']:
                with open(export_path, 'w') as f:
                    yaml.dump(branding_config, f, default_flow_style=False, indent=2)
            # Export as JSON
            elif export_path.suffix.lower() == '.json':
                with open(export_path, 'w') as f:
                    json.dump(branding_config, f, indent=2)
            else:
                # Default to YAML
                export_path = export_path.with_suffix('.yaml')
                with open(export_path, 'w') as f:
                    yaml.dump(branding_config, f, default_flow_style=False, indent=2)
            
            log.info(f"Exported branding configuration for {client_name} to {export_path}")
            return True
            
        except Exception as e:
            log.error(f"Error exporting branding configuration for {client_name}: {e}")
            return False

    def import_branding_config(self, import_path: Path, client_name: Optional[str] = None) -> bool:
        """
        Import a branding configuration from a file.
        
        Args:
            import_path: Path to the configuration file
            client_name: Name for the client (if not specified in config)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load configuration
            if import_path.suffix.lower() in ['.yaml', '.yml']:
                with open(import_path, 'r') as f:
                    branding_config = yaml.safe_load(f)
            elif import_path.suffix.lower() == '.json':
                with open(import_path, 'r') as f:
                    branding_config = json.load(f)
            else:
                log.error(f"Unsupported file format: {import_path.suffix}")
                return False
            
            # Validate configuration
            errors = self.validate_branding_config(branding_config)
            if errors:
                log.error(f"Invalid branding configuration: {errors}")
                return False
            
            # Use specified client name or name from config
            if client_name:
                branding_config['name'] = client_name
            elif 'name' not in branding_config:
                branding_config['name'] = import_path.stem
            
            # Create client branding
            self.create_client_branding(branding_config['name'], branding_config)
            return True
            
        except Exception as e:
            log.error(f"Error importing branding configuration: {e}")
            return False

    def get_branding_summary(self, client_name: str) -> Dict[str, Any]:
        """
        Get a summary of a client's branding configuration.
        
        Args:
            client_name: Name of the client
            
        Returns:
            Dictionary containing branding summary
        """
        try:
            branding_config = self.get_client_branding(client_name)
            if not branding_config:
                return {}
            
            summary = {
                'client_name': branding_config.get('name', client_name),
                'colors': list(branding_config.get('colors', {}).keys()),
                'fonts': list(branding_config.get('fonts', {}).keys()),
                'has_logo': 'logo' in branding_config,
                'has_footer_logo': 'footer_logo' in branding_config,
                'page_margins': branding_config.get('page_margins', {}),
                'header_text': branding_config.get('header', {}).get('left_text', ''),
                'footer_text': branding_config.get('footer', {}).get('left_text', '')
            }
            
            return summary
            
        except Exception as e:
            log.error(f"Error getting branding summary for {client_name}: {e}")
            return {}
