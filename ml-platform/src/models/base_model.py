"""
Base Model Class

Abstract base class for all ML models in the platform.
Provides common functionality for training, validation, and MLflow integration.
"""

import os
import pickle
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, Union
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_squared_error, r2_score

logger = logging.getLogger(__name__)


class BaseModel(ABC):
    """Abstract base class for ML models with MLflow integration."""
    
    def __init__(self, model_name: str, experiment_name: str = "default"):
        """
        Initialize base model.
        
        Args:
            model_name: Name of the model
            experiment_name: MLflow experiment name
        """
        self.model_name = model_name
        self.experiment_name = experiment_name
        self.model = None
        self.is_trained = False
        self.feature_names = None
        
        # Setup MLflow
        mlflow.set_experiment(experiment_name)
        
    @abstractmethod
    def create_model(self, **kwargs) -> Any:
        """Create and return the ML model instance."""
        pass
    
    @abstractmethod
    def evaluate_model(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        """Evaluate model and return metrics."""
        pass
    
    def prepare_data(self, 
                    data: pd.DataFrame, 
                    target_column: str,
                    test_size: float = 0.2,
                    random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare data for training.
        
        Args:
            data: Input dataframe
            target_column: Name of target column
            test_size: Fraction of data for testing
            random_state: Random seed
            
        Returns:
            X_train, X_test, y_train, y_test
        """
        logger.info(f"Preparing data with {len(data)} samples")
        
        # Separate features and target
        X = data.drop(columns=[target_column])
        y = data[target_column]
        
        # Store feature names
        self.feature_names = list(X.columns)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        logger.info(f"Training set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")
        
        return X_train, X_test, y_train, y_test
    
    def train(self, 
              X_train: pd.DataFrame, 
              y_train: pd.Series,
              X_test: pd.DataFrame,
              y_test: pd.Series,
              **model_params) -> Dict[str, float]:
        """
        Train the model with MLflow tracking.
        
        Args:
            X_train: Training features
            y_train: Training target
            X_test: Test features  
            y_test: Test target
            **model_params: Model hyperparameters
            
        Returns:
            Dictionary of evaluation metrics
        """
        with mlflow.start_run(run_name=f"{self.model_name}_training"):
            # Log parameters
            mlflow.log_params(model_params)
            mlflow.log_param("model_name", self.model_name)
            mlflow.log_param("train_samples", len(X_train))
            mlflow.log_param("test_samples", len(X_test))
            
            # Create and train model
            self.model = self.create_model(**model_params)
            
            logger.info("Starting model training...")
            self.model.fit(X_train, y_train)
            self.is_trained = True
            
            # Evaluate model
            metrics = self.evaluate_model(X_test, y_test)
            
            # Log metrics
            mlflow.log_metrics(metrics)
            
            # Log model
            mlflow.sklearn.log_model(
                self.model,
                "model",
                registered_model_name=self.model_name
            )
            
            logger.info(f"Model training completed. Metrics: {metrics}")
            
            return metrics
    
    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Make predictions.
        
        Args:
            X: Input features
            
        Returns:
            Predictions
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
            
        return self.model.predict(X)
    
    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Get prediction probabilities (for classification models).
        
        Args:
            X: Input features
            
        Returns:
            Prediction probabilities
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
            
        if not hasattr(self.model, 'predict_proba'):
            raise ValueError("Model does not support probability predictions")
            
        return self.model.predict_proba(X)
    
    def save_model(self, filepath: str) -> None:
        """
        Save model to disk.
        
        Args:
            filepath: Path to save model
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
            
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'model_name': self.model_name,
                'feature_names': self.feature_names,
                'is_trained': self.is_trained
            }, f)
            
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """
        Load model from disk.
        
        Args:
            filepath: Path to load model from
        """
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
            
        self.model = model_data['model']
        self.model_name = model_data['model_name']
        self.feature_names = model_data['feature_names']
        self.is_trained = model_data['is_trained']
        
        logger.info(f"Model loaded from {filepath}")