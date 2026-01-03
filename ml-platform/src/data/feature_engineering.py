"""
Feature Engineering

Feature transformation and engineering utilities.
Includes scaling, encoding, feature selection, and custom transformations.
"""

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union, Tuple, Any
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler, RobustScaler,
    LabelEncoder, OneHotEncoder, OrdinalEncoder
)
from sklearn.feature_selection import (
    SelectKBest, SelectPercentile, RFE, RFECV,
    f_classif, f_regression, mutual_info_classif, mutual_info_regression
)
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
import joblib

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Feature engineering pipeline with preprocessing and transformations."""
    
    def __init__(self):
        """Initialize feature engineer."""
        self.preprocessor = None
        self.feature_selector = None
        self.is_fitted = False
        self.feature_names_in_ = None
        self.feature_names_out_ = None
        
    def create_preprocessor(self,
                          numeric_features: List[str],
                          categorical_features: List[str],
                          numeric_strategy: str = "standard",
                          categorical_strategy: str = "onehot") -> ColumnTransformer:
        """
        Create preprocessing pipeline.
        
        Args:
            numeric_features: List of numeric feature names
            categorical_features: List of categorical feature names
            numeric_strategy: Scaling strategy ('standard', 'minmax', 'robust')
            categorical_strategy: Encoding strategy ('onehot', 'ordinal', 'label')
            
        Returns:
            ColumnTransformer for preprocessing
        """
        # Numeric transformers
        numeric_transformers = {
            'standard': StandardScaler(),
            'minmax': MinMaxScaler(),
            'robust': RobustScaler()
        }
        
        # Categorical transformers
        categorical_transformers = {
            'onehot': OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore'),
            'ordinal': OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1),
            'label': LabelEncoder()
        }
        
        # Build transformers list
        transformers = []
        
        if numeric_features:
            transformers.append((
                'numeric',
                numeric_transformers[numeric_strategy],
                numeric_features
            ))
            
        if categorical_features:
            transformers.append((
                'categorical',
                categorical_transformers[categorical_strategy],
                categorical_features
            ))
        
        self.preprocessor = ColumnTransformer(
            transformers=transformers,
            remainder='passthrough'
        )
        
        logger.info(f"Created preprocessor with {len(transformers)} transformers")
        return self.preprocessor
    
    def fit_transform(self, 
                     X: pd.DataFrame, 
                     y: Optional[pd.Series] = None) -> np.ndarray:
        """
        Fit preprocessor and transform data.
        
        Args:
            X: Input features
            y: Target variable (optional)
            
        Returns:
            Transformed features
        """
        if self.preprocessor is None:
            raise ValueError("Preprocessor not created. Call create_preprocessor first.")
            
        self.feature_names_in_ = list(X.columns)
        X_transformed = self.preprocessor.fit_transform(X)
        self.is_fitted = True
        
        # Get output feature names
        self._set_output_feature_names()
        
        logger.info(f"Fitted preprocessor on {X.shape[0]} samples, {X.shape[1]} features")
        logger.info(f"Output shape: {X_transformed.shape}")
        
        return X_transformed
    
    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """
        Transform data using fitted preprocessor.
        
        Args:
            X: Input features
            
        Returns:
            Transformed features
        """
        if not self.is_fitted:
            raise ValueError("Preprocessor not fitted. Call fit_transform first.")
            
        return self.preprocessor.transform(X)
    
    def _set_output_feature_names(self):
        """Set output feature names after fitting."""
        try:
            if hasattr(self.preprocessor, 'get_feature_names_out'):
                self.feature_names_out_ = list(self.preprocessor.get_feature_names_out())
            else:
                # Fallback for older sklearn versions
                self.feature_names_out_ = [f'feature_{i}' for i in range(
                    self.preprocessor.transform(pd.DataFrame(columns=self.feature_names_in_)).shape[1]
                )]
        except:
            self.feature_names_out_ = None
    
    def select_features(self,
                       X: np.ndarray,
                       y: pd.Series,
                       method: str = "k_best",
                       k: int = 10,
                       task_type: str = "classification") -> np.ndarray:
        """
        Select features using various methods.
        
        Args:
            X: Input features (transformed)
            y: Target variable
            method: Selection method ('k_best', 'percentile', 'rfe', 'rfecv')
            k: Number of features to select (for k_best and rfe)
            task_type: 'classification' or 'regression'
            
        Returns:
            Selected features
        """
        # Choose scoring function
        if task_type == "classification":
            score_func = f_classif
            mutual_info_func = mutual_info_classif
        else:
            score_func = f_regression
            mutual_info_func = mutual_info_regression
        
        # Feature selection methods
        if method == "k_best":
            self.feature_selector = SelectKBest(score_func=score_func, k=k)
        elif method == "percentile":
            self.feature_selector = SelectPercentile(score_func=score_func, percentile=k)
        elif method == "mutual_info":
            self.feature_selector = SelectKBest(score_func=mutual_info_func, k=k)
        elif method == "rfe":
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            if task_type == "classification":
                estimator = RandomForestClassifier(n_estimators=50, random_state=42)
            else:
                estimator = RandomForestRegressor(n_estimators=50, random_state=42)
            self.feature_selector = RFE(estimator=estimator, n_features_to_select=k)
        elif method == "rfecv":
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            if task_type == "classification":
                estimator = RandomForestClassifier(n_estimators=50, random_state=42)
            else:
                estimator = RandomForestRegressor(n_estimators=50, random_state=42)
            self.feature_selector = RFECV(estimator=estimator, cv=5)
        else:
            raise ValueError(f"Unknown feature selection method: {method}")
        
        # Fit and transform
        X_selected = self.feature_selector.fit_transform(X, y)
        
        logger.info(f"Selected {X_selected.shape[1]} features from {X.shape[1]} using {method}")
        
        return X_selected
    
    def get_selected_feature_names(self) -> List[str]:
        """Get names of selected features."""
        if self.feature_selector is None:
            return self.feature_names_out_ or []
            
        if self.feature_names_out_ is None:
            return [f'feature_{i}' for i in range(self.feature_selector.transform(
                np.zeros((1, len(self.feature_names_in_)))
            ).shape[1])]
        
        # Get selected feature mask
        if hasattr(self.feature_selector, 'get_support'):
            mask = self.feature_selector.get_support()
            return [name for name, selected in zip(self.feature_names_out_, mask) if selected]
        
        return self.feature_names_out_
    
    def save_pipeline(self, filepath: str):
        """Save the feature engineering pipeline."""
        pipeline_data = {
            'preprocessor': self.preprocessor,
            'feature_selector': self.feature_selector,
            'is_fitted': self.is_fitted,
            'feature_names_in_': self.feature_names_in_,
            'feature_names_out_': self.feature_names_out_
        }
        
        joblib.dump(pipeline_data, filepath)
        logger.info(f"Pipeline saved to {filepath}")
    
    def load_pipeline(self, filepath: str):
        """Load the feature engineering pipeline."""
        pipeline_data = joblib.load(filepath)
        
        self.preprocessor = pipeline_data['preprocessor']
        self.feature_selector = pipeline_data['feature_selector']
        self.is_fitted = pipeline_data['is_fitted']
        self.feature_names_in_ = pipeline_data['feature_names_in_']
        self.feature_names_out_ = pipeline_data['feature_names_out_']
        
        logger.info(f"Pipeline loaded from {filepath}")


class CustomTransformers:
    """Collection of custom transformers for specific use cases."""
    
    class DateTimeFeatureExtractor(BaseEstimator, TransformerMixin):
        """Extract features from datetime columns."""
        
        def __init__(self, datetime_columns: List[str]):
            self.datetime_columns = datetime_columns
            
        def fit(self, X, y=None):
            return self
            
        def transform(self, X):
            X_copy = X.copy()
            
            for col in self.datetime_columns:
                if col in X_copy.columns:
                    dt_col = pd.to_datetime(X_copy[col])
                    
                    # Extract features
                    X_copy[f'{col}_year'] = dt_col.dt.year
                    X_copy[f'{col}_month'] = dt_col.dt.month
                    X_copy[f'{col}_day'] = dt_col.dt.day
                    X_copy[f'{col}_dayofweek'] = dt_col.dt.dayofweek
                    X_copy[f'{col}_hour'] = dt_col.dt.hour
                    X_copy[f'{col}_is_weekend'] = dt_col.dt.dayofweek.isin([5, 6]).astype(int)
                    
                    # Drop original column
                    X_copy = X_copy.drop(columns=[col])
                    
            return X_copy
    
    class OutlierClipper(BaseEstimator, TransformerMixin):
        """Clip outliers using IQR method."""
        
        def __init__(self, columns: List[str], factor: float = 1.5):
            self.columns = columns
            self.factor = factor
            self.bounds_ = {}
            
        def fit(self, X, y=None):
            for col in self.columns:
                if col in X.columns:
                    Q1 = X[col].quantile(0.25)
                    Q3 = X[col].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    lower_bound = Q1 - self.factor * IQR
                    upper_bound = Q3 + self.factor * IQR
                    
                    self.bounds_[col] = (lower_bound, upper_bound)
                    
            return self
            
        def transform(self, X):
            X_copy = X.copy()
            
            for col, (lower, upper) in self.bounds_.items():
                if col in X_copy.columns:
                    X_copy[col] = X_copy[col].clip(lower, upper)
                    
            return X_copy
    
    class PolynomialFeatures(BaseEstimator, TransformerMixin):
        """Create polynomial features for specified columns."""
        
        def __init__(self, columns: List[str], degree: int = 2):
            self.columns = columns
            self.degree = degree
            
        def fit(self, X, y=None):
            return self
            
        def transform(self, X):
            X_copy = X.copy()
            
            for col in self.columns:
                if col in X_copy.columns:
                    for d in range(2, self.degree + 1):
                        X_copy[f'{col}_poly_{d}'] = X_copy[col] ** d
                        
            return X_copy


# Example usage
def feature_engineering_example():
    """Example of feature engineering workflow."""
    # Create sample data
    np.random.seed(42)
    data = pd.DataFrame({
        'numeric_1': np.random.normal(0, 1, 1000),
        'numeric_2': np.random.uniform(0, 100, 1000),
        'numeric_3': np.random.exponential(2, 1000),
        'categorical_1': np.random.choice(['A', 'B', 'C', 'D'], 1000),
        'categorical_2': np.random.choice(['X', 'Y'], 1000),
        'target': np.random.randint(0, 2, 1000)
    })
    
    # Initialize feature engineer
    fe = FeatureEngineer()
    
    # Define feature types
    numeric_features = ['numeric_1', 'numeric_2', 'numeric_3']
    categorical_features = ['categorical_1', 'categorical_2']
    
    # Create preprocessor
    fe.create_preprocessor(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        numeric_strategy='standard',
        categorical_strategy='onehot'
    )
    
    # Fit and transform
    X = data.drop('target', axis=1)
    y = data['target']
    
    X_transformed = fe.fit_transform(X)
    print(f"Original shape: {X.shape}")
    print(f"Transformed shape: {X_transformed.shape}")
    
    # Feature selection
    X_selected = fe.select_features(
        X_transformed, y, 
        method='k_best', 
        k=5, 
        task_type='classification'
    )
    print(f"Selected features shape: {X_selected.shape}")
    
    # Get selected feature names
    selected_names = fe.get_selected_feature_names()
    print(f"Selected features: {selected_names}")
    
    # Save pipeline
    fe.save_pipeline('feature_pipeline.joblib')
    
    return fe, X_transformed, X_selected


if __name__ == "__main__":
    fe, X_transformed, X_selected = feature_engineering_example()