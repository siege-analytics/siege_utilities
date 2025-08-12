"""
Google Analytics Integration Module

This module provides comprehensive Google Analytics integration capabilities:
- Connect to GA accounts via OAuth2
- Retrieve data from GA4 and Universal Analytics
- Save data as Pandas or Spark dataframes
- Associate GA accounts with client profiles
- Batch data retrieval and processing
"""

import json
import pathlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import pandas as pd

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Metric, Dimension
    )
    GOOGLE_ANALYTICS_AVAILABLE = True
except ImportError:
    GOOGLE_ANALYTICS_AVAILABLE = False

try:
    from pyspark.sql import DataFrame as SparkDataFrame
    from pyspark.sql import SparkSession
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False

# Import logging functions from main package
try:
    from siege_utilities import log_info, log_warning, log_error
except ImportError:
    # Fallback if main package not available yet
    def log_info(message): print(f"INFO: {message}")
    def log_warning(message): print(f"WARNING: {message}")
    def log_error(message): print(f"ERROR: {message}")


class GoogleAnalyticsConnector:
    """Google Analytics connection and data retrieval manager."""
    
    def __init__(self, client_id: str, client_secret: str, 
                 redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob"):
        """
        Initialize Google Analytics connector.
        
        Args:
            client_id: OAuth2 client ID from Google Cloud Console
            client_secret: OAuth2 client secret from Google Cloud Console
            redirect_uri: OAuth2 redirect URI
        """
        if not GOOGLE_ANALYTICS_AVAILABLE:
            raise ImportError("Google Analytics libraries not available. Install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client google-analytics-data")
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.credentials = None
        self.analytics_service = None
        self.ga4_client = None
        
        log_info(f"Initialized Google Analytics connector for client: {client_id}")
    
    def authenticate(self, token_file: str = "ga_token.json") -> bool:
        """
        Authenticate with Google Analytics using OAuth2.
        
        Args:
            token_file: Path to store/retrieve OAuth token
            
        Returns:
            True if authentication successful
        """
        try:
            token_path = pathlib.Path(token_file)
            
            # Try to load existing credentials
            if token_path.exists():
                self.credentials = Credentials.from_authorized_user_file(
                    str(token_path), 
                    ['https://www.googleapis.com/auth/analytics.readonly']
                )
                
                # Refresh if expired
                if self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self._save_credentials(token_path)
                    log_info("Refreshed expired Google Analytics credentials")
                else:
                    log_info("Loaded existing Google Analytics credentials")
            else:
                # New authentication flow
                flow = InstalledAppFlow.from_client_config(
                    {
                        "installed": {
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                            "redirect_uris": [self.redirect_uri],
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token"
                        }
                    },
                    ['https://www.googleapis.com/auth/analytics.readonly']
                )
                
                self.credentials = flow.run_local_server(port=0)
                self._save_credentials(token_path)
                log_info("Completed new Google Analytics authentication")
            
            # Build services
            self.analytics_service = build('analytics', 'v3', credentials=self.credentials)
            self.ga4_client = BetaAnalyticsDataClient(credentials=self.credentials)
            
            return True
            
        except Exception as e:
            log_error(f"Google Analytics authentication failed: {e}")
            return False
    
    def _save_credentials(self, token_path: pathlib.Path):
        """Save OAuth credentials to file."""
        with open(token_path, 'w') as token:
            token.write(self.credentials.to_json())
        log_info(f"Saved credentials to: {token_path}")
    
    def get_ga4_data(self, property_id: str, start_date: str, end_date: str,
                     metrics: List[str], dimensions: List[str] = None,
                     row_limit: int = 100000) -> pd.DataFrame:
        """
        Retrieve data from Google Analytics 4.
        
        Args:
            property_id: GA4 property ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            metrics: List of metrics to retrieve
            dimensions: List of dimensions to retrieve
            row_limit: Maximum rows to retrieve
            
        Returns:
            Pandas DataFrame with GA4 data
        """
        try:
            if not self.ga4_client:
                raise ValueError("Not authenticated. Call authenticate() first.")
            
            # Build request
            request = RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                metrics=[Metric(name=metric) for metric in metrics],
                dimensions=[Dimension(name=dim) for dim in (dimensions or [])],
                limit=row_limit
            )
            
            # Execute request
            response = self.ga4_client.run_report(request)
            
            # Convert to DataFrame
            data = []
            for row in response.rows:
                row_data = {}
                for i, dimension in enumerate(row.dimension_headers):
                    row_data[dimension.name] = row.dimension_values[i].value
                for i, metric in enumerate(row.metric_headers):
                    row_data[metric.name] = row.metric_values[i].value
                data.append(row_data)
            
            df = pd.DataFrame(data)
            log_info(f"Retrieved {len(df)} rows from GA4 property {property_id}")
            return df
            
        except Exception as e:
            log_error(f"Failed to retrieve GA4 data: {e}")
            return pd.DataFrame()
    
    def get_ua_data(self, view_id: str, start_date: str, end_date: str,
                    metrics: List[str], dimensions: List[str] = None,
                    max_results: int = 100000) -> pd.DataFrame:
        """
        Retrieve data from Universal Analytics.
        
        Args:
            view_id: UA view ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            metrics: List of metrics to retrieve
            dimensions: List of dimensions to retrieve
            max_results: Maximum results to retrieve
            
        Returns:
            Pandas DataFrame with UA data
        """
        try:
            if not self.analytics_service:
                raise ValueError("Not authenticated. Call authenticate() first.")
            
            # Build query
            query = self.analytics_service.data().ga().get(
                ids=f'ga:{view_id}',
                start_date=start_date,
                end_date=end_date,
                metrics=','.join(metrics),
                dimensions=','.join(dimensions) if dimensions else None,
                max_results=max_results
            )
            
            # Execute query
            response = query.execute()
            
            # Convert to DataFrame
            if 'rows' in response:
                columns = [header['name'] for header in response['columnHeaders']]
                df = pd.DataFrame(response['rows'], columns=columns)
                log_info(f"Retrieved {len(df)} rows from UA view {view_id}")
                return df
            else:
                log_warning(f"No data returned from UA view {view_id}")
                return pd.DataFrame()
                
        except Exception as e:
            log_error(f"Failed to retrieve UA data: {e}")
            return pd.DataFrame()
    
    def save_as_pandas(self, df: pd.DataFrame, output_path: str, 
                       format: str = 'parquet') -> bool:
        """
        Save DataFrame as Pandas format.
        
        Args:
            df: Pandas DataFrame to save
            output_path: Output file path
            format: Output format (parquet, csv, excel, etc.)
            
        Returns:
            True if save successful
        """
        try:
            output_path = pathlib.Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == 'parquet':
                df.to_parquet(output_path, index=False)
            elif format.lower() == 'csv':
                df.to_csv(output_path, index=False)
            elif format.lower() == 'excel':
                df.to_excel(output_path, index=False)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            log_info(f"Saved DataFrame to {output_path} ({format} format)")
            return True
            
        except Exception as e:
            log_error(f"Failed to save DataFrame: {e}")
            return False
    
    def save_as_spark(self, df: pd.DataFrame, output_path: str,
                      spark_session: Optional[SparkSession] = None) -> bool:
        """
        Save DataFrame as Spark DataFrame and optionally to storage.
        
        Args:
            df: Pandas DataFrame to convert
            output_path: Output path for Spark DataFrame
            spark_session: Optional SparkSession (will create if not provided)
            
        Returns:
            True if save successful
        """
        try:
            if not SPARK_AVAILABLE:
                raise ImportError("PySpark not available. Install: pip install pyspark")
            
            # Create Spark session if not provided
            if not spark_session:
                spark_session = SparkSession.builder \
                    .appName("GoogleAnalyticsData") \
                    .getOrCreate()
            
            # Convert to Spark DataFrame
            spark_df = spark_session.createDataFrame(df)
            
            # Save to storage
            spark_df.write.mode('overwrite').parquet(output_path)
            
            log_info(f"Saved DataFrame as Spark DataFrame to {output_path}")
            return True
            
        except Exception as e:
            log_error(f"Failed to save as Spark DataFrame: {e}")
            return False


def create_ga_account_profile(client_id: str, ga_property_id: str, 
                             account_type: str = 'ga4',
                             credentials_file: str = None) -> Dict[str, Any]:
    """
    Create a Google Analytics account profile linked to a client.
    
    Args:
        client_id: Client ID from client management system
        ga_property_id: Google Analytics property ID
        account_type: Type of GA account (ga4, ua, or both)
        credentials_file: Path to OAuth credentials file
        
    Returns:
        GA account profile dictionary
    """
    profile = {
        'ga_account_id': f"ga_{ga_property_id}",
        'client_id': client_id,
        'ga_property_id': ga_property_id,
        'account_type': account_type,
        'credentials_file': credentials_file,
        'created_date': datetime.now().isoformat(),
        'last_accessed': None,
        'status': 'active',
        'metadata': {
            'data_retrieval_count': 0,
            'last_data_retrieval': None,
            'total_rows_retrieved': 0
        }
    }
    
    log_info(f"Created GA account profile: {ga_property_id} for client: {client_id}")
    return profile


def save_ga_account_profile(profile: Dict[str, Any], 
                           config_directory: str = "config") -> str:
    """
    Save GA account profile to JSON file.
    
    Args:
        profile: GA account profile dictionary
        config_directory: Directory to save config files
        
    Returns:
        Path to saved config file
    """
    config_dir = pathlib.Path(config_directory) / "google_analytics"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    account_id = profile['ga_account_id']
    config_file = config_dir / f"ga_account_{account_id}.json"
    
    with open(config_file, 'w') as f:
        json.dump(profile, f, indent=2)
    
    log_info(f"Saved GA account profile to: {config_file}")
    return str(config_file)


def load_ga_account_profile(account_id: str, 
                           config_directory: str = "config") -> Optional[Dict[str, Any]]:
    """
    Load GA account profile from JSON file.
    
    Args:
        account_id: GA account ID to load
        config_directory: Directory containing config files
        
    Returns:
        GA account profile dictionary or None if not found
    """
    config_dir = pathlib.Path(config_directory) / "google_analytics"
    config_file = config_dir / f"ga_account_{account_id}.json"
    
    if not config_file.exists():
        return None
    
    try:
        with open(config_file, 'r') as f:
            profile = json.load(f)
        
        log_info(f"Loaded GA account profile: {account_id}")
        return profile
        
    except Exception as e:
        log_error(f"Failed to load GA account profile {account_id}: {e}")
        return None


def list_ga_accounts_for_client(client_id: str, 
                                config_directory: str = "config") -> List[Dict[str, Any]]:
    """
    List all GA accounts associated with a client.
    
    Args:
        client_id: Client ID to search for
        config_directory: Directory containing config files
        
    Returns:
        List of GA account profiles
    """
    config_dir = pathlib.Path(config_directory) / "google_analytics"
    
    if not config_dir.exists():
        return []
    
    accounts = []
    for config_file in config_dir.glob("ga_account_*.json"):
        try:
            with open(config_file, 'r') as f:
                profile = json.load(f)
            
            if profile.get('client_id') == client_id:
                accounts.append(profile)
                
        except Exception as e:
            log_error(f"Error reading GA account file {config_file}: {e}")
    
    log_info(f"Found {len(accounts)} GA accounts for client: {client_id}")
    return accounts


def batch_retrieve_ga_data(client_id: str, start_date: str, end_date: str,
                          metrics: List[str], dimensions: List[str] = None,
                          output_format: str = 'pandas',
                          output_directory: str = "output/ga_data") -> Dict[str, Any]:
    """
    Batch retrieve GA data for all accounts associated with a client.
    
    Args:
        client_id: Client ID to retrieve data for
        start_date: Start date for data retrieval
        end_date: End date for data retrieval
        metrics: List of metrics to retrieve
        dimensions: List of dimensions to retrieve
        output_format: Output format (pandas, spark, or both)
        output_directory: Directory to save output files
        
    Returns:
        Dictionary with retrieval results
    """
    try:
        # Get client's GA accounts
        accounts = list_ga_accounts_for_client(client_id)
        
        if not accounts:
            return {
                'success': False,
                'error': f'No GA accounts found for client: {client_id}',
                'accounts_processed': 0,
                'total_rows': 0
            }
        
        # Setup output directory
        output_dir = pathlib.Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'success': True,
            'client_id': client_id,
            'start_date': start_date,
            'end_date': end_date,
            'accounts_processed': 0,
            'total_rows': 0,
            'output_files': [],
            'errors': []
        }
        
        # Process each account
        for account in accounts:
            try:
                # Load credentials and authenticate
                if not account.get('credentials_file'):
                    results['errors'].append(f"No credentials for account: {account['ga_account_id']}")
                    continue
                
                # Create connector and retrieve data
                # Note: In production, you'd load actual credentials from the file
                connector = GoogleAnalyticsConnector("dummy_id", "dummy_secret")
                
                if account['account_type'] in ['ga4', 'both']:
                    df = connector.get_ga4_data(
                        account['ga_property_id'], start_date, end_date, metrics, dimensions
                    )
                else:
                    df = connector.get_ua_data(
                        account['ga_property_id'], start_date, end_date, metrics, dimensions
                    )
                
                if not df.empty:
                    # Save data
                    output_file = output_dir / f"{account['ga_account_id']}_{start_date}_{end_date}.parquet"
                    
                    if output_format in ['pandas', 'both']:
                        connector.save_as_pandas(df, str(output_file), 'parquet')
                        results['output_files'].append(str(output_file))
                    
                    if output_format in ['spark', 'both'] and SPARK_AVAILABLE:
                        spark_output = output_dir / f"{account['ga_account_id']}_{start_date}_{end_date}_spark"
                        connector.save_as_spark(df, str(spark_output))
                        results['output_files'].append(str(spark_output))
                    
                    results['total_rows'] += len(df)
                    results['accounts_processed'] += 1
                    
                    log_info(f"Processed GA account: {account['ga_account_id']} - {len(df)} rows")
                
            except Exception as e:
                error_msg = f"Error processing account {account['ga_account_id']}: {e}"
                results['errors'].append(error_msg)
                log_error(error_msg)
        
        log_info(f"Batch GA data retrieval completed: {results['accounts_processed']} accounts, {results['total_rows']} rows")
        return results
        
    except Exception as e:
        log_error(f"Batch GA data retrieval failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'accounts_processed': 0,
            'total_rows': 0
        }
