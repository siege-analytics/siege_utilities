"""
Facebook Business Integration Module

This module provides comprehensive Facebook Business integration capabilities:
- Connect to Facebook Business accounts via OAuth2
- Retrieve data from Facebook Ads, Pages, and Business Manager
- Save data as Pandas or Spark dataframes
- Associate Facebook accounts with client profiles
- Batch data retrieval and processing
"""

import json
import pathlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import pandas as pd

try:
    import facebook_business
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.page import Page
    from facebook_business.adobjects.business import Business
    FACEBOOK_BUSINESS_AVAILABLE = True
except ImportError:
    FACEBOOK_BUSINESS_AVAILABLE = False

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


class FacebookBusinessConnector:
    """Facebook Business connection and data retrieval manager."""
    
    def __init__(self, access_token: str, app_id: str = None, app_secret: str = None):
        """
        Initialize Facebook Business connector.
        
        Args:
            access_token: Facebook access token
            app_id: Facebook app ID (optional)
            app_secret: Facebook app secret (optional)
        """
        if not FACEBOOK_BUSINESS_AVAILABLE:
            raise ImportError("Facebook Business libraries not available. Install: pip install facebook-business")
        
        self.access_token = access_token
        self.app_id = app_id
        self.app_secret = app_secret
        self.api = None
        
        # Initialize Facebook API
        if app_id and app_secret:
            FacebookAdsApi.init(app_id, app_secret, access_token)
        else:
            FacebookAdsApi.init(access_token=access_token)
        
        self.api = FacebookAdsApi.get_default_api()
        log_info(f"Initialized Facebook Business connector")
    
    def get_ad_accounts(self) -> List[Dict[str, Any]]:
        """
        Get list of accessible ad accounts.
        
        Returns:
            List of ad account information
        """
        try:
            me = facebook_business.adobjects.user.User(fbid='me')
            ad_accounts = me.get_ad_accounts()
            
            accounts = []
            for account in ad_accounts:
                account_data = {
                    'id': account['id'],
                    'name': account['name'],
                    'account_status': account['account_status'],
                    'currency': account['currency'],
                    'timezone_name': account['timezone_name']
                }
                accounts.append(account_data)
            
            log_info(f"Retrieved {len(accounts)} Facebook ad accounts")
            return accounts
            
        except Exception as e:
            log_error(f"Failed to retrieve ad accounts: {e}")
            return []
    
    def get_ad_insights(self, ad_account_id: str, start_date: str, end_date: str,
                        fields: List[str] = None, breakdowns: List[str] = None) -> pd.DataFrame:
        """
        Retrieve ad insights from Facebook Ads.
        
        Args:
            ad_account_id: Facebook ad account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            fields: List of insight fields to retrieve
            breakdowns: List of breakdowns to apply
            
        Returns:
            Pandas DataFrame with ad insights
        """
        try:
            if not fields:
                fields = [
                    'impressions', 'clicks', 'spend', 'reach', 'frequency',
                    'cpm', 'cpc', 'ctr', 'actions', 'action_values'
                ]
            
            ad_account = AdAccount(ad_account_id)
            insights = ad_account.get_insights(
                fields=fields,
                params={
                    'time_range': {
                        'since': start_date,
                        'until': end_date
                    },
                    'breakdowns': breakdowns or [],
                    'level': 'ad'
                }
            )
            
            # Convert to DataFrame
            data = []
            for insight in insights:
                insight_data = {}
                for field in fields:
                    insight_data[field] = insight.get(field, 0)
                
                # Add breakdown data
                if breakdowns:
                    for breakdown in breakdowns:
                        insight_data[f'breakdown_{breakdown}'] = insight.get(breakdown, '')
                
                data.append(insight_data)
            
            df = pd.DataFrame(data)
            log_info(f"Retrieved {len(df)} ad insights from account {ad_account_id}")
            return df
            
        except Exception as e:
            log_error(f"Failed to retrieve ad insights: {e}")
            return pd.DataFrame()
    
    def get_page_insights(self, page_id: str, start_date: str, end_date: str,
                          metrics: List[str] = None) -> pd.DataFrame:
        """
        Retrieve page insights from Facebook Pages.
        
        Args:
            page_id: Facebook page ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            metrics: List of metrics to retrieve
            
        Returns:
            Pandas DataFrame with page insights
        """
        try:
            if not metrics:
                metrics = [
                    'page_impressions', 'page_engaged_users', 'page_post_engagements',
                    'page_fans', 'page_views_total', 'page_actions_post_reactions_total'
                ]
            
            page = Page(page_id)
            insights = page.get_insights(
                fields=metrics,
                params={
                    'period': 'day',
                    'since': start_date,
                    'until': end_date
                }
            )
            
            # Convert to DataFrame
            data = []
            for insight in insights:
                insight_data = {}
                for metric in metrics:
                    values = insight.get('values', [])
                    if values:
                        insight_data['date'] = values[0].get('end_time', '')
                        insight_data[metric] = values[0].get('value', 0)
                    else:
                        insight_data['date'] = ''
                        insight_data[metric] = 0
                
                data.append(insight_data)
            
            df = pd.DataFrame(data)
            log_info(f"Retrieved {len(df)} page insights from page {page_id}")
            return df
            
        except Exception as e:
            log_error(f"Failed to retrieve page insights: {e}")
            return pd.DataFrame()
    
    def get_business_insights(self, business_id: str, start_date: str, end_date: str,
                              metrics: List[str] = None) -> pd.DataFrame:
        """
        Retrieve business insights from Facebook Business Manager.
        
        Args:
            business_id: Facebook business ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            metrics: List of metrics to retrieve
            
        Returns:
            Pandas DataFrame with business insights
        """
        try:
            if not metrics:
                metrics = [
                    'spend', 'impressions', 'clicks', 'reach', 'frequency',
                    'cpm', 'cpc', 'ctr', 'actions', 'action_values'
                ]
            
            business = Business(business_id)
            insights = business.get_insights(
                fields=metrics,
                params={
                    'time_range': {
                        'since': start_date,
                        'until': end_date
                    },
                    'level': 'business'
                }
            )
            
            # Convert to DataFrame
            data = []
            for insight in insights:
                insight_data = {}
                for metric in metrics:
                    insight_data[metric] = insight.get(metric, 0)
                data.append(insight_data)
            
            df = pd.DataFrame(data)
            log_info(f"Retrieved {len(df)} business insights from business {business_id}")
            return df
            
        except Exception as e:
            log_error(f"Failed to retrieve business insights: {e}")
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
                    .appName("FacebookBusinessData") \
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


def create_facebook_account_profile(client_id: str, fb_account_id: str, 
                                   account_type: str = 'ad_account',
                                   access_token: str = None) -> Dict[str, Any]:
    """
    Create a Facebook account profile linked to a client.
    
    Args:
        client_id: Client ID from client management system
        fb_account_id: Facebook account ID
        account_type: Type of FB account (ad_account, page, business)
        access_token: Facebook access token
        
    Returns:
        Facebook account profile dictionary
    """
    profile = {
        'fb_account_id': f"fb_{fb_account_id}",
        'client_id': client_id,
        'fb_account_id_raw': fb_account_id,
        'account_type': account_type,
        'access_token': access_token,
        'created_date': datetime.now().isoformat(),
        'last_accessed': None,
        'status': 'active',
        'metadata': {
            'data_retrieval_count': 0,
            'last_data_retrieval': None,
            'total_rows_retrieved': 0
        }
    }
    
    log_info(f"Created Facebook account profile: {fb_account_id} for client: {client_id}")
    return profile


def save_facebook_account_profile(profile: Dict[str, Any], 
                                 config_directory: str = "config") -> str:
    """
    Save Facebook account profile to JSON file.
    
    Args:
        profile: Facebook account profile dictionary
        config_directory: Directory to save config files
        
    Returns:
        Path to saved config file
    """
    config_dir = pathlib.Path(config_directory) / "facebook_business"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    account_id = profile['fb_account_id']
    config_file = config_dir / f"fb_account_{account_id}.json"
    
    with open(config_file, 'w') as f:
        json.dump(profile, f, indent=2)
    
    log_info(f"Saved Facebook account profile to: {config_file}")
    return str(config_file)


def load_facebook_account_profile(account_id: str, 
                                 config_directory: str = "config") -> Optional[Dict[str, Any]]:
    """
    Load Facebook account profile from JSON file.
    
    Args:
        account_id: Facebook account ID to load
        config_directory: Directory containing config files
        
    Returns:
        Facebook account profile dictionary or None if not found
    """
    config_dir = pathlib.Path(config_directory) / "facebook_business"
    config_file = config_dir / f"fb_account_{account_id}.json"
    
    if not config_file.exists():
        return None
    
    try:
        with open(config_file, 'r') as f:
            profile = json.load(f)
        
        log_info(f"Loaded Facebook account profile: {account_id}")
        return profile
        
    except Exception as e:
        log_error(f"Failed to load Facebook account profile {account_id}: {e}")
        return None


def list_facebook_accounts_for_client(client_id: str, 
                                     config_directory: str = "config") -> List[Dict[str, Any]]:
    """
    List all Facebook accounts associated with a client.
    
    Args:
        client_id: Client ID to search for
        config_directory: Directory containing config files
        
    Returns:
        List of Facebook account profiles
    """
    config_dir = pathlib.Path(config_directory) / "facebook_business"
    
    if not config_dir.exists():
        return []
    
    accounts = []
    for config_file in config_dir.glob("fb_account_*.json"):
        try:
            with open(config_file, 'r') as f:
                profile = json.load(f)
            
            if profile.get('client_id') == client_id:
                accounts.append(profile)
                
        except Exception as e:
            log_error(f"Error reading Facebook account file {config_file}: {e}")
    
    log_info(f"Found {len(accounts)} Facebook accounts for client: {client_id}")
    return accounts


def batch_retrieve_facebook_data(client_id: str, start_date: str, end_date: str,
                                 data_types: List[str] = None, output_format: str = 'pandas',
                                 output_directory: str = "output/facebook_data") -> Dict[str, Any]:
    """
    Batch retrieve Facebook data for all accounts associated with a client.
    
    Args:
        client_id: Client ID to retrieve data for
        start_date: Start date for data retrieval
        end_date: End date for data retrieval
        data_types: Types of data to retrieve (ads, pages, business)
        output_format: Output format (pandas, spark, or both)
        output_directory: Directory to save output files
        
    Returns:
        Dictionary with retrieval results
    """
    try:
        # Get client's Facebook accounts
        accounts = list_facebook_accounts_for_client(client_id)
        
        if not accounts:
            return {
                'success': False,
                'error': f'No Facebook accounts found for client: {client_id}',
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
                # Load access token
                if not account.get('access_token'):
                    results['errors'].append(f"No access token for account: {account['fb_account_id']}")
                    continue
                
                # Create connector
                connector = FacebookBusinessConnector(account['access_token'])
                
                # Retrieve data based on account type
                if account['account_type'] == 'ad_account':
                    df = connector.get_ad_insights(
                        account['fb_account_id_raw'], start_date, end_date
                    )
                elif account['account_type'] == 'page':
                    df = connector.get_page_insights(
                        account['fb_account_id_raw'], start_date, end_date
                    )
                elif account['account_type'] == 'business':
                    df = connector.get_business_insights(
                        account['fb_account_id_raw'], start_date, end_date
                    )
                else:
                    results['errors'].append(f"Unknown account type: {account['account_type']}")
                    continue
                
                if not df.empty:
                    # Save data
                    output_file = output_dir / f"{account['fb_account_id']}_{start_date}_{end_date}.parquet"
                    
                    if output_format in ['pandas', 'both']:
                        connector.save_as_pandas(df, str(output_file), 'parquet')
                        results['output_files'].append(str(output_file))
                    
                    if output_format in ['spark', 'both'] and SPARK_AVAILABLE:
                        spark_output = output_dir / f"{account['fb_account_id']}_{start_date}_{end_date}_spark"
                        connector.save_as_spark(df, str(spark_output))
                        results['output_files'].append(str(spark_output))
                    
                    results['total_rows'] += len(df)
                    results['accounts_processed'] += 1
                    
                    log_info(f"Processed Facebook account: {account['fb_account_id']} - {len(df)} rows")
                
            except Exception as e:
                error_msg = f"Error processing account {account['fb_account_id']}: {e}"
                results['errors'].append(error_msg)
                log_error(error_msg)
        
        log_info(f"Batch Facebook data retrieval completed: {results['accounts_processed']} accounts, {results['total_rows']} rows")
        return results
        
    except Exception as e:
        log_error(f"Batch Facebook data retrieval failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'accounts_processed': 0,
            'total_rows': 0
        }
