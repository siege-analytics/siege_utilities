"""
Data.world connector for Siege Utilities.

Provides seamless integration with data.world for data discovery, access, and collaboration.
"""

import logging
from typing import Optional, Dict, List, Any, Union
from pathlib import Path
import json
import os

try:
    import datadotworld as dw
    DATADOTWORLD_AVAILABLE = True
except ImportError:
    DATADOTWORLD_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

log = logging.getLogger(__name__)


class DataDotWorldConnector:
    """Data.world connector with advanced data discovery and access features."""
    
    def __init__(self, 
                 api_token: Optional[str] = None,
                 config_file: Optional[Union[str, Path]] = None):
        """
        Initialize Data.world connector.
        
        Args:
            api_token: Data.world API token (optional if using config file)
            config_file: Path to configuration file
        """
        if not DATADOTWORLD_AVAILABLE:
            raise ImportError("Data.world connector not available. Install with: pip install datadotworld")
        
        self.api_token = api_token
        self.config_file = config_file
        
        # Load configuration if provided
        if config_file:
            self._load_config(config_file)
        
        # Initialize client
        self.client = None
        self._initialize_client()
        
        log.info("Initialized Data.world connector")
    
    def _load_config(self, config_file: Union[str, Path]) -> None:
        """Load configuration from file."""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update instance variables with config values
            if 'api_token' in config and config['api_token']:
                self.api_token = config['api_token']
                    
        except Exception as e:
            log.error(f"Failed to load configuration: {e}")
            raise
    
    def _initialize_client(self) -> None:
        """Initialize the Data.world client."""
        try:
            if self.api_token:
                self.client = dw.api_client(self.api_token)
            else:
                # Try to get from environment variable
                env_token = os.getenv('DATADOTWORLD_API_TOKEN')
                if env_token:
                    self.client = dw.api_client(env_token)
                else:
                    # Use anonymous client
                    self.client = dw.api_client()
                    log.warning("No API token provided. Using anonymous access with limited functionality.")
            
            log.info("Data.world client initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize Data.world client: {e}")
            raise
    
    def search_datasets(self, 
                       query: str,
                       limit: int = 50,
                       owner: Optional[str] = None,
                       tags: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Search for datasets on data.world.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            owner: Filter by dataset owner
            tags: Filter by tags
            
        Returns:
            List of dataset information dictionaries
        """
        try:
            # Build search parameters
            search_params = {
                'q': query,
                'limit': limit
            }
            
            if owner:
                search_params['owner'] = owner
            if tags:
                search_params['tags'] = ','.join(tags)
            
            # Perform search
            search_results = self.client.search_datasets(**search_params)
            
            # Extract relevant information
            datasets = []
            for result in search_results['records']:
                dataset_info = {
                    'id': result.get('id'),
                    'title': result.get('title'),
                    'description': result.get('description'),
                    'owner': result.get('owner'),
                    'tags': result.get('tags', []),
                    'license': result.get('license'),
                    'visibility': result.get('visibility'),
                    'updated_at': result.get('updatedAt'),
                    'download_count': result.get('downloadCount', 0)
                }
                datasets.append(dataset_info)
            
            log.info(f"Found {len(datasets)} datasets matching query: {query}")
            return datasets
            
        except Exception as e:
            log.error(f"Dataset search failed: {e}")
            return None
    
    def get_dataset_info(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific dataset.
        
        Args:
            dataset_id: Dataset identifier (format: owner/dataset)
            
        Returns:
            Dictionary with detailed dataset information
        """
        try:
            dataset_info = self.client.get_dataset(dataset_id)
            
            # Extract relevant information
            info = {
                'id': dataset_info.get('id'),
                'title': dataset_info.get('title'),
                'description': dataset_info.get('description'),
                'owner': dataset_info.get('owner'),
                'tags': dataset_info.get('tags', []),
                'license': dataset_info.get('license'),
                'visibility': dataset_info.get('visibility'),
                'created_at': dataset_info.get('createdAt'),
                'updated_at': dataset_info.get('updatedAt'),
                'download_count': dataset_info.get('downloadCount', 0),
                'files': dataset_info.get('files', []),
                'summary': dataset_info.get('summary', {})
            }
            
            log.info(f"Retrieved dataset info for: {dataset_id}")
            return info
            
        except Exception as e:
            log.error(f"Failed to get dataset info for {dataset_id}: {e}")
            return None
    
    def list_dataset_files(self, dataset_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        List all files in a dataset.
        
        Args:
            dataset_id: Dataset identifier (format: owner/dataset)
            
        Returns:
            List of file information dictionaries
        """
        try:
            dataset_info = self.client.get_dataset(dataset_id)
            files = dataset_info.get('files', [])
            
            # Extract relevant file information
            file_list = []
            for file_info in files:
                file_data = {
                    'name': file_info.get('name'),
                    'size': file_info.get('size'),
                    'format': file_info.get('format'),
                    'url': file_info.get('url'),
                    'description': file_info.get('description'),
                    'tags': file_info.get('tags', [])
                }
                file_list.append(file_data)
            
            log.info(f"Found {len(file_list)} files in dataset: {dataset_id}")
            return file_list
            
        except Exception as e:
            log.error(f"Failed to list files for dataset {dataset_id}: {e}")
            return None
    
    def download_file(self, 
                     dataset_id: str,
                     file_name: str,
                     output_path: Optional[Union[str, Path]] = None) -> Optional[Union[str, Path]]:
        """
        Download a specific file from a dataset.
        
        Args:
            dataset_id: Dataset identifier (format: owner/dataset)
            file_name: Name of the file to download
            output_path: Local path to save the file (optional)
            
        Returns:
            Path to the downloaded file
        """
        try:
            if not output_path:
                # Use default download directory
                from siege_utilities.files import get_download_directory
                output_path = get_download_directory() / "datadotworld" / dataset_id.replace('/', '_') / file_name
            
            # Ensure output directory exists
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download the file
            self.client.download_file(dataset_id, file_name, output_path)
            
            log.info(f"Successfully downloaded {file_name} to {output_path}")
            return output_path
            
        except Exception as e:
            log.error(f"Failed to download file {file_name} from dataset {dataset_id}: {e}")
            return None
    
    def load_dataset_as_dataframe(self, 
                                 dataset_id: str,
                                 file_name: Optional[str] = None) -> Optional['pd.DataFrame']:
        """
        Load a dataset file directly as a pandas DataFrame.
        
        Args:
            dataset_id: Dataset identifier (format: owner/dataset)
            file_name: Name of the file to load (optional, loads first file if not specified)
            
        Returns:
            Pandas DataFrame with the data
        """
        if not PANDAS_AVAILABLE:
            log.error("Pandas not available for DataFrame operations")
            return None
        
        try:
            if file_name:
                # Load specific file
                df = dw.load_dataset(dataset_id, file_name)
            else:
                # Load entire dataset
                df = dw.load_dataset(dataset_id)
            
            log.info(f"Successfully loaded dataset {dataset_id} as DataFrame with {len(df)} rows")
            return df
            
        except Exception as e:
            log.error(f"Failed to load dataset {dataset_id} as DataFrame: {e}")
            return None
    
    def query_dataset(self, 
                     dataset_id: str,
                     query: str,
                     query_type: str = 'sql') -> Optional['pd.DataFrame']:
        """
        Execute a query against a dataset.
        
        Args:
            dataset_id: Dataset identifier (format: owner/dataset)
            query: Query string (SQL or SPARQL)
            query_type: Type of query ('sql' or 'sparql')
            
        Returns:
            Pandas DataFrame with query results
        """
        if not PANDAS_AVAILABLE:
            log.error("Pandas not available for DataFrame operations")
            return None
        
        try:
            if query_type.lower() == 'sql':
                df = dw.query(dataset_id, query, query_type='sql')
            elif query_type.lower() == 'sparql':
                df = dw.query(dataset_id, query, query_type='sparql')
            else:
                raise ValueError("query_type must be 'sql' or 'sparql'")
            
            log.info(f"Successfully executed {query_type.upper()} query on dataset {dataset_id}")
            return df
            
        except Exception as e:
            log.error(f"Query execution failed on dataset {dataset_id}: {e}")
            return None
    
    def get_dataset_schema(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema information for a dataset.
        
        Args:
            dataset_id: Dataset identifier (format: owner/dataset)
            
        Returns:
            Dictionary with schema information
        """
        try:
            dataset_info = self.client.get_dataset(dataset_id)
            schema = dataset_info.get('schema', {})
            
            log.info(f"Retrieved schema for dataset: {dataset_id}")
            return schema
            
        except Exception as e:
            log.error(f"Failed to get schema for dataset {dataset_id}: {e}")
            return None
    
    def create_dataset(self, 
                      owner: str,
                      dataset_id: str,
                      title: str,
                      description: str,
                      tags: Optional[List[str]] = None,
                      license: str = 'Public Domain',
                      visibility: str = 'OPEN') -> Optional[str]:
        """
        Create a new dataset on data.world.
        
        Args:
            owner: Dataset owner username
            dataset_id: Unique dataset identifier
            title: Dataset title
            description: Dataset description
            tags: List of tags (optional)
            license: Dataset license (optional)
            visibility: Dataset visibility ('OPEN' or 'PRIVATE')
            
        Returns:
            Created dataset ID if successful, None otherwise
        """
        try:
            if not self.api_token:
                raise ValueError("API token required to create datasets")
            
            # Create dataset
            dataset_info = self.client.create_dataset(
                owner=owner,
                id=dataset_id,
                title=title,
                description=description,
                tags=tags or [],
                license=license,
                visibility=visibility
            )
            
            created_id = f"{owner}/{dataset_id}"
            log.info(f"Successfully created dataset: {created_id}")
            return created_id
            
        except Exception as e:
            log.error(f"Failed to create dataset: {e}")
            return None
    
    def upload_file(self, 
                   dataset_id: str,
                   file_path: Union[str, Path],
                   file_name: Optional[str] = None) -> bool:
        """
        Upload a file to an existing dataset.
        
        Args:
            dataset_id: Dataset identifier (format: owner/dataset)
            file_path: Local path to the file to upload
            file_name: Name to use for the file on data.world (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.api_token:
                raise ValueError("API token required to upload files")
            
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not file_name:
                file_name = file_path.name
            
            # Upload the file
            self.client.upload_file(dataset_id, file_path, file_name)
            
            log.info(f"Successfully uploaded {file_name} to dataset {dataset_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to upload file to dataset {dataset_id}: {e}")
            return False
    
    def update_dataset(self, 
                      dataset_id: str,
                      title: Optional[str] = None,
                      description: Optional[str] = None,
                      tags: Optional[List[str]] = None,
                      license: Optional[str] = None) -> bool:
        """
        Update an existing dataset.
        
        Args:
            dataset_id: Dataset identifier (format: owner/dataset)
            title: New title (optional)
            description: New description (optional)
            tags: New tags (optional)
            license: New license (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.api_token:
                raise ValueError("API token required to update datasets")
            
            # Build update parameters
            update_params = {}
            if title:
                update_params['title'] = title
            if description:
                update_params['description'] = description
            if tags:
                update_params['tags'] = tags
            if license:
                update_params['license'] = license
            
            if not update_params:
                log.warning("No update parameters provided")
                return False
            
            # Update dataset
            self.client.update_dataset(dataset_id, **update_params)
            
            log.info(f"Successfully updated dataset: {dataset_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to update dataset {dataset_id}: {e}")
            return False
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a dataset.
        
        Args:
            dataset_id: Dataset identifier (format: owner/dataset)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.api_token:
                raise ValueError("API token required to delete datasets")
            
            # Delete dataset
            self.client.delete_dataset(dataset_id)
            
            log.info(f"Successfully deleted dataset: {dataset_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to delete dataset {dataset_id}: {e}")
            return False


# Convenience functions
def get_datadotworld_connector(config_file: Optional[Union[str, Path]] = None) -> DataDotWorldConnector:
    """Get Data.world connector instance from configuration."""
    return DataDotWorldConnector(config_file=config_file)


def search_datadotworld_datasets(query: str, 
                                config_file: Optional[Union[str, Path]] = None,
                                **kwargs) -> Optional[List[Dict[str, Any]]]:
    """Convenience function to search for datasets."""
    with get_datadotworld_connector(config_file) as dw:
        return dw.search_datasets(query, **kwargs)


def load_datadotworld_dataset(dataset_id: str,
                             config_file: Optional[Union[str, Path]] = None,
                             **kwargs) -> Optional['pd.DataFrame']:
    """Convenience function to load a dataset as DataFrame."""
    with get_datadotworld_connector(config_file) as dw:
        return dw.load_dataset_as_dataframe(dataset_id, **kwargs)


def query_datadotworld_dataset(dataset_id: str,
                              query: str,
                              config_file: Optional[Union[str, Path]] = None,
                              **kwargs) -> Optional['pd.DataFrame']:
    """Convenience function to query a dataset."""
    with get_datadotworld_connector(config_file) as dw:
        return dw.query_dataset(dataset_id, query, **kwargs)


# Global instance for easy access
datadotworld_connector = None

__all__ = [
    'DataDotWorldConnector',
    'get_datadotworld_connector',
    'search_datadotworld_datasets',
    'load_datadotworld_dataset',
    'query_datadotworld_dataset',
    'datadotworld_connector',
    'DATADOTWORLD_AVAILABLE'
]
