"""
Test Data Processing

Unit tests for data loading, validation, and feature engineering.
"""

import os
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
import numpy as np
import tempfile

from data.data_loader import DataLoader
from data.feature_engineering import FeatureEngineer


class TestDataLoader:
    """Test data loader functionality."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data."""
        np.random.seed(42)
        return pd.DataFrame({
            'numeric_1': np.random.normal(0, 1, 100),
            'numeric_2': np.random.uniform(0, 100, 100),
            'categorical_1': np.random.choice(['A', 'B', 'C'], 100),
            'categorical_2': np.random.choice(['X', 'Y'], 100),
            'target': np.random.randint(0, 2, 100)
        })
    
    def test_initialization(self):
        """Test data loader initialization."""
        loader = DataLoader(aws_region="us-west-2", s3_bucket="test-bucket")
        
        assert loader.aws_region == "us-west-2"
        assert loader.s3_bucket == "test-bucket"
    
    def test_load_local_csv(self, sample_data):
        """Test loading CSV from local filesystem."""
        loader = DataLoader()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            sample_data.to_csv(f.name, index=False)
            temp_path = f.name
        
        try:
            loaded_data = loader.load_csv(temp_path, source="local")
            
            assert loaded_data.shape == sample_data.shape
            assert list(loaded_data.columns) == list(sample_data.columns)
            pd.testing.assert_frame_equal(loaded_data, sample_data)
            
        finally:
            os.unlink(temp_path)
    
    def test_load_local_parquet(self, sample_data):
        """Test loading Parquet from local filesystem."""
        loader = DataLoader()
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            sample_data.to_parquet(f.name, index=False)
            temp_path = f.name
        
        try:
            loaded_data = loader.load_parquet(temp_path, source="local")
            
            assert loaded_data.shape == sample_data.shape
            assert list(loaded_data.columns) == list(sample_data.columns)
            
        finally:
            os.unlink(temp_path)
    
    def test_save_local_data(self, sample_data):
        """Test saving data to local filesystem."""
        loader = DataLoader()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test CSV
            csv_path = os.path.join(temp_dir, "test.csv")
            loader.save_data(sample_data, csv_path, format="csv", source="local")
            
            assert os.path.exists(csv_path)
            loaded_csv = pd.read_csv(csv_path)
            assert loaded_csv.shape == sample_data.shape
            
            # Test Parquet
            parquet_path = os.path.join(temp_dir, "test.parquet")
            loader.save_data(sample_data, parquet_path, format="parquet", source="local")
            
            assert os.path.exists(parquet_path)
            loaded_parquet = pd.read_parquet(parquet_path)
            assert loaded_parquet.shape == sample_data.shape
    
    def test_create_sample_data(self):
        """Test sample data creation."""
        loader = DataLoader()
        
        # Test classification data
        classification_data = loader.create_sample_data(
            n_samples=100,
            n_features=5,
            task_type="classification"
        )
        
        assert classification_data.shape == (100, 6)  # 5 features + target
        assert 'target' in classification_data.columns
        assert classification_data['target'].dtype in ['int64', 'int32']
        
        # Test regression data
        regression_data = loader.create_sample_data(
            n_samples=100,
            n_features=5,
            task_type="regression"
        )
        
        assert regression_data.shape == (100, 6)  # 5 features + target
        assert 'target' in regression_data.columns
        assert regression_data['target'].dtype in ['float64', 'float32']
    
    def test_unsupported_format(self, sample_data):
        """Test error handling for unsupported formats."""
        loader = DataLoader()
        
        with pytest.raises(ValueError):
            loader.load_csv("test.csv", source="unsupported_source")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError):
                loader.save_data(
                    sample_data, 
                    os.path.join(temp_dir, "test.txt"), 
                    format="unsupported_format"
                )


class TestFeatureEngineer:
    """Test feature engineering functionality."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data with mixed types."""
        np.random.seed(42)
        return pd.DataFrame({
            'numeric_1': np.random.normal(0, 1, 100),
            'numeric_2': np.random.uniform(0, 100, 100),
            'numeric_3': np.random.exponential(2, 100),
            'categorical_1': np.random.choice(['A', 'B', 'C', 'D'], 100),
            'categorical_2': np.random.choice(['X', 'Y'], 100),
            'target': np.random.randint(0, 2, 100)
        })
    
    def test_initialization(self):
        """Test feature engineer initialization."""
        fe = FeatureEngineer()
        
        assert fe.preprocessor is None
        assert fe.feature_selector is None
        assert not fe.is_fitted
    
    def test_create_preprocessor(self, sample_data):
        """Test preprocessor creation."""
        fe = FeatureEngineer()
        
        numeric_features = ['numeric_1', 'numeric_2', 'numeric_3']
        categorical_features = ['categorical_1', 'categorical_2']
        
        preprocessor = fe.create_preprocessor(
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            numeric_strategy='standard',
            categorical_strategy='onehot'
        )
        
        assert preprocessor is not None
        assert fe.preprocessor is not None
    
    def test_fit_transform(self, sample_data):
        """Test fitting and transforming data."""
        fe = FeatureEngineer()
        
        numeric_features = ['numeric_1', 'numeric_2', 'numeric_3']
        categorical_features = ['categorical_1', 'categorical_2']
        
        fe.create_preprocessor(
            numeric_features=numeric_features,
            categorical_features=categorical_features
        )
        
        X = sample_data.drop('target', axis=1)
        X_transformed = fe.fit_transform(X)
        
        assert fe.is_fitted
        assert X_transformed.shape[0] == X.shape[0]
        assert X_transformed.shape[1] > X.shape[1]  # One-hot encoding increases features
    
    def test_transform_after_fit(self, sample_data):
        """Test transforming new data after fitting."""
        fe = FeatureEngineer()
        
        numeric_features = ['numeric_1', 'numeric_2', 'numeric_3']
        categorical_features = ['categorical_1', 'categorical_2']
        
        fe.create_preprocessor(
            numeric_features=numeric_features,
            categorical_features=categorical_features
        )
        
        X = sample_data.drop('target', axis=1)
        
        # Fit on first half
        X_train = X.iloc[:50]
        X_transformed_train = fe.fit_transform(X_train)
        
        # Transform second half
        X_test = X.iloc[50:]
        X_transformed_test = fe.transform(X_test)
        
        assert X_transformed_train.shape[1] == X_transformed_test.shape[1]
    
    def test_feature_selection(self, sample_data):
        """Test feature selection."""
        fe = FeatureEngineer()
        
        numeric_features = ['numeric_1', 'numeric_2', 'numeric_3']
        categorical_features = ['categorical_1', 'categorical_2']
        
        fe.create_preprocessor(
            numeric_features=numeric_features,
            categorical_features=categorical_features
        )
        
        X = sample_data.drop('target', axis=1)
        y = sample_data['target']
        
        X_transformed = fe.fit_transform(X)
        X_selected = fe.select_features(
            X_transformed, y, 
            method='k_best', 
            k=3, 
            task_type='classification'
        )
        
        assert X_selected.shape[1] == 3
        assert X_selected.shape[0] == X_transformed.shape[0]
    
    def test_get_selected_feature_names(self, sample_data):
        """Test getting selected feature names."""
        fe = FeatureEngineer()
        
        numeric_features = ['numeric_1', 'numeric_2', 'numeric_3']
        categorical_features = ['categorical_1', 'categorical_2']
        
        fe.create_preprocessor(
            numeric_features=numeric_features,
            categorical_features=categorical_features
        )
        
        X = sample_data.drop('target', axis=1)
        y = sample_data['target']
        
        X_transformed = fe.fit_transform(X)
        X_selected = fe.select_features(
            X_transformed, y, 
            method='k_best', 
            k=3, 
            task_type='classification'
        )
        
        selected_names = fe.get_selected_feature_names()
        assert len(selected_names) == 3
        assert all(isinstance(name, str) for name in selected_names)
    
    def test_save_load_pipeline(self, sample_data):
        """Test saving and loading feature pipeline."""
        fe = FeatureEngineer()
        
        numeric_features = ['numeric_1', 'numeric_2', 'numeric_3']
        categorical_features = ['categorical_1', 'categorical_2']
        
        fe.create_preprocessor(
            numeric_features=numeric_features,
            categorical_features=categorical_features
        )
        
        X = sample_data.drop('target', axis=1)
        X_transformed = fe.fit_transform(X)
        
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save pipeline
            fe.save_pipeline(temp_path)
            assert os.path.exists(temp_path)
            
            # Load pipeline
            fe_new = FeatureEngineer()
            fe_new.load_pipeline(temp_path)
            
            assert fe_new.is_fitted
            assert fe_new.feature_names_in_ == fe.feature_names_in_
            
            # Test that loaded pipeline works
            X_transformed_new = fe_new.transform(X)
            np.testing.assert_array_equal(X_transformed, X_transformed_new)
            
        finally:
            os.unlink(temp_path)
    
    def test_error_handling(self, sample_data):
        """Test error handling."""
        fe = FeatureEngineer()
        
        X = sample_data.drop('target', axis=1)
        
        # Test transform without fit
        with pytest.raises(ValueError):
            fe.transform(X)
        
        # Test feature selection without preprocessor
        with pytest.raises(ValueError):
            fe.select_features(X.values, sample_data['target'])


if __name__ == "__main__":
    pytest.main([__file__])