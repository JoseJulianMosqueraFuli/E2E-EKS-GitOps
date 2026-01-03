"""
Data Loader

Utilities for loading data from various sources including S3, local files,
and databases. Supports multiple formats and includes data validation.
"""

import logging
import os
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import numpy as np
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import yaml

logger = logging.getLogger(__name__)


class DataLoader:
    """Data loading utilities for various sources and formats."""
    
    def __init__(self, 
                 aws_region: str = "us-west-2",
                 s3_bucket: Optional[str] = None):
        """
        Initialize data loader.
        
        Args:
            aws_region: AWS region for S3 operations
            s3_bucket: Default S3 bucket name
        """
        self.aws_region = aws_region
        self.s3_bucket = s3_bucket
        self.s3_client = None
        
        # Initialize S3 client if credentials available
        try:
            self.s3_client = boto3.client('s3', region_name=aws_region)
            logger.info("S3 client initialized successfully")
        except (NoCredentialsError, Exception) as e:
            logger.warning(f"Could not initialize S3 client: {e}")
    
    def load_csv(self, 
                 filepath: str,
                 source: str = "local",
                 **kwargs) -> pd.DataFrame:
        """
        Load CSV file from local or S3.
        
        Args:
            filepath: Path to CSV file
            source: 'local' or 's3'
            **kwargs: Additional pandas.read_csv parameters
            
        Returns:
            DataFrame
        """
        if source == "local":
            return self._load_local_csv(filepath, **kwargs)
        elif source == "s3":
            return self._load_s3_csv(filepath, **kwargs)
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def _load_local_csv(self, filepath: str, **kwargs) -> pd.DataFrame:
        """Load CSV from local filesystem."""
        try:
            df = pd.read_csv(filepath, **kwargs)
            logger.info(f"Loaded CSV from {filepath}: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV from {filepath}: {e}")
            raise
    
    def _load_s3_csv(self, s3_key: str, bucket: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """Load CSV from S3."""
        if self.s3_client is None:
            raise ValueError("S3 client not available")
            
        bucket = bucket or self.s3_bucket
        if not bucket:
            raise ValueError("S3 bucket not specified")
        
        try:
            # Get object from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=s3_key)
            
            # Read CSV
            df = pd.read_csv(response['Body'], **kwargs)
            logger.info(f"Loaded CSV from s3://{bucket}/{s3_key}: {df.shape}")
            return df
            
        except ClientError as e:
            logger.error(f"Error loading CSV from S3: {e}")
            raise
    
    def load_parquet(self,
                    filepath: str,
                    source: str = "local",
                    **kwargs) -> pd.DataFrame:
        """
        Load Parquet file from local or S3.
        
        Args:
            filepath: Path to Parquet file
            source: 'local' or 's3'
            **kwargs: Additional pandas.read_parquet parameters
            
        Returns:
            DataFrame
        """
        if source == "local":
            return self._load_local_parquet(filepath, **kwargs)
        elif source == "s3":
            return self._load_s3_parquet(filepath, **kwargs)
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def _load_local_parquet(self, filepath: str, **kwargs) -> pd.DataFrame:
        """Load Parquet from local filesystem."""
        try:
            df = pd.read_parquet(filepath, **kwargs)
            logger.info(f"Loaded Parquet from {filepath}: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Error loading Parquet from {filepath}: {e}")
            raise
    
    def _load_s3_parquet(self, s3_key: str, bucket: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """Load Parquet from S3."""
        bucket = bucket or self.s3_bucket
        if not bucket:
            raise ValueError("S3 bucket not specified")
        
        try:
            # Use s3fs for parquet reading
            s3_path = f"s3://{bucket}/{s3_key}"
            df = pd.read_parquet(s3_path, **kwargs)
            logger.info(f"Loaded Parquet from {s3_path}: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading Parquet from S3: {e}")
            raise
    
    def load_json(self,
                 filepath: str,
                 source: str = "local",
                 **kwargs) -> pd.DataFrame:
        """
        Load JSON file from local or S3.
        
        Args:
            filepath: Path to JSON file
            source: 'local' or 's3'
            **kwargs: Additional pandas.read_json parameters
            
        Returns:
            DataFrame
        """
        if source == "local":
            return self._load_local_json(filepath, **kwargs)
        elif source == "s3":
            return self._load_s3_json(filepath, **kwargs)
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def _load_local_json(self, filepath: str, **kwargs) -> pd.DataFrame:
        """Load JSON from local filesystem."""
        try:
            df = pd.read_json(filepath, **kwargs)
            logger.info(f"Loaded JSON from {filepath}: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Error loading JSON from {filepath}: {e}")
            raise
    
    def _load_s3_json(self, s3_key: str, bucket: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """Load JSON from S3."""
        if self.s3_client is None:
            raise ValueError("S3 client not available")
            
        bucket = bucket or self.s3_bucket
        if not bucket:
            raise ValueError("S3 bucket not specified")
        
        try:
            # Get object from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=s3_key)
            
            # Read JSON
            df = pd.read_json(response['Body'], **kwargs)
            logger.info(f"Loaded JSON from s3://{bucket}/{s3_key}: {df.shape}")
            return df
            
        except ClientError as e:
            logger.error(f"Error loading JSON from S3: {e}")
            raise
    
    def save_data(self,
                 df: pd.DataFrame,
                 filepath: str,
                 format: str = "csv",
                 source: str = "local",
                 **kwargs):
        """
        Save DataFrame to various formats and destinations.
        
        Args:
            df: DataFrame to save
            filepath: Destination path
            format: File format ('csv', 'parquet', 'json')
            source: 'local' or 's3'
            **kwargs: Additional save parameters
        """
        if source == "local":
            self._save_local(df, filepath, format, **kwargs)
        elif source == "s3":
            self._save_s3(df, filepath, format, **kwargs)
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def _save_local(self, df: pd.DataFrame, filepath: str, format: str, **kwargs):
        """Save DataFrame to local filesystem."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        try:
            if format == "csv":
                df.to_csv(filepath, index=False, **kwargs)
            elif format == "parquet":
                df.to_parquet(filepath, index=False, **kwargs)
            elif format == "json":
                df.to_json(filepath, **kwargs)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
            logger.info(f"Saved {format.upper()} to {filepath}: {df.shape}")
            
        except Exception as e:
            logger.error(f"Error saving {format.upper()} to {filepath}: {e}")
            raise
    
    def _save_s3(self, df: pd.DataFrame, s3_key: str, format: str, bucket: Optional[str] = None, **kwargs):
        """Save DataFrame to S3."""
        if self.s3_client is None:
            raise ValueError("S3 client not available")
            
        bucket = bucket or self.s3_bucket
        if not bucket:
            raise ValueError("S3 bucket not specified")
        
        try:
            # Save to temporary file first
            temp_file = f"/tmp/{os.path.basename(s3_key)}"
            
            if format == "csv":
                df.to_csv(temp_file, index=False, **kwargs)
            elif format == "parquet":
                df.to_parquet(temp_file, index=False, **kwargs)
            elif format == "json":
                df.to_json(temp_file, **kwargs)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Upload to S3
            self.s3_client.upload_file(temp_file, bucket, s3_key)
            
            # Clean up temp file
            os.remove(temp_file)
            
            logger.info(f"Saved {format.upper()} to s3://{bucket}/{s3_key}: {df.shape}")
            
        except Exception as e:
            logger.error(f"Error saving {format.upper()} to S3: {e}")
            raise
    
    def list_s3_objects(self, prefix: str = "", bucket: Optional[str] = None) -> List[str]:
        """
        List objects in S3 bucket with given prefix.
        
        Args:
            prefix: Object key prefix
            bucket: S3 bucket name
            
        Returns:
            List of object keys
        """
        if self.s3_client is None:
            raise ValueError("S3 client not available")
            
        bucket = bucket or self.s3_bucket
        if not bucket:
            raise ValueError("S3 bucket not specified")
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            objects = []
            if 'Contents' in response:
                objects = [obj['Key'] for obj in response['Contents']]
                
            logger.info(f"Found {len(objects)} objects in s3://{bucket}/{prefix}")
            return objects
            
        except ClientError as e:
            logger.error(f"Error listing S3 objects: {e}")
            raise
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to config file
            
        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded config from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            raise
    
    def create_sample_data(self, 
                          n_samples: int = 1000,
                          n_features: int = 10,
                          task_type: str = "classification") -> pd.DataFrame:
        """
        Create sample data for testing.
        
        Args:
            n_samples: Number of samples
            n_features: Number of features
            task_type: 'classification' or 'regression'
            
        Returns:
            Sample DataFrame
        """
        np.random.seed(42)
        
        # Generate features
        data = {}
        for i in range(n_features):
            if i % 3 == 0:
                # Numeric features
                data[f'numeric_{i}'] = np.random.normal(0, 1, n_samples)
            elif i % 3 == 1:
                # Categorical features
                data[f'categorical_{i}'] = np.random.choice(['A', 'B', 'C'], n_samples)
            else:
                # Mixed features
                data[f'mixed_{i}'] = np.random.uniform(0, 100, n_samples)
        
        # Generate target
        if task_type == "classification":
            data['target'] = np.random.randint(0, 3, n_samples)
        else:
            data['target'] = np.random.normal(50, 10, n_samples)
        
        df = pd.DataFrame(data)
        logger.info(f"Created sample {task_type} data: {df.shape}")
        
        return df


# Example usage
def data_loading_example():
    """Example of data loading workflow."""
    # Initialize data loader
    loader = DataLoader(s3_bucket="mlops-dev-raw-data")
    
    # Create sample data
    sample_data = loader.create_sample_data(
        n_samples=1000,
        n_features=5,
        task_type="classification"
    )
    
    print(f"Sample data shape: {sample_data.shape}")
    print(f"Sample data columns: {list(sample_data.columns)}")
    print(f"Target distribution:\n{sample_data['target'].value_counts()}")
    
    # Save locally
    loader.save_data(sample_data, "data/sample_data.csv", format="csv")
    loader.save_data(sample_data, "data/sample_data.parquet", format="parquet")
    
    # Load back
    loaded_csv = loader.load_csv("data/sample_data.csv")
    loaded_parquet = loader.load_parquet("data/sample_data.parquet")
    
    print(f"Loaded CSV shape: {loaded_csv.shape}")
    print(f"Loaded Parquet shape: {loaded_parquet.shape}")
    
    return loader, sample_data


if __name__ == "__main__":
    loader, sample_data = data_loading_example()