"""
Regression Model

Implementation of regression models with MLflow integration.
Supports multiple algorithms: RandomForest, XGBoost, LinearRegression.
"""

import logging
from typing import Any, Dict
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error
)
import mlflow

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

from .base_model import BaseModel

logger = logging.getLogger(__name__)


class RegressionModel(BaseModel):
    """Regression model with support for multiple algorithms."""
    
    SUPPORTED_ALGORITHMS = {
        'random_forest': RandomForestRegressor,
        'linear_regression': LinearRegression,
        'ridge': Ridge,
        'lasso': Lasso,
    }
    
    if XGBOOST_AVAILABLE:
        SUPPORTED_ALGORITHMS['xgboost'] = XGBRegressor
    
    def __init__(self, 
                 model_name: str = "regression_model",
                 algorithm: str = "random_forest",
                 experiment_name: str = "regression_experiments"):
        """
        Initialize regression model.
        
        Args:
            model_name: Name of the model
            algorithm: Algorithm to use
            experiment_name: MLflow experiment name
        """
        super().__init__(model_name, experiment_name)
        
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(f"Algorithm {algorithm} not supported. "
                           f"Available: {list(self.SUPPORTED_ALGORITHMS.keys())}")
        
        self.algorithm = algorithm
        self.algorithm_class = self.SUPPORTED_ALGORITHMS[algorithm]
        
    def create_model(self, **kwargs) -> Any:
        """
        Create regression model instance.
        
        Args:
            **kwargs: Model hyperparameters
            
        Returns:
            Model instance
        """
        # Default parameters for each algorithm
        default_params = {
            'random_forest': {
                'n_estimators': 100,
                'max_depth': 10,
                'random_state': 42,
                'n_jobs': -1
            },
            'linear_regression': {},
            'ridge': {
                'alpha': 1.0,
                'random_state': 42
            },
            'lasso': {
                'alpha': 1.0,
                'random_state': 42,
                'max_iter': 1000
            }
        }
        
        if XGBOOST_AVAILABLE:
            default_params['xgboost'] = {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'random_state': 42
            }
        
        # Merge default params with provided params
        params = default_params.get(self.algorithm, {})
        params.update(kwargs)
        
        logger.info(f"Creating {self.algorithm} model with params: {params}")
        
        return self.algorithm_class(**params)
    
    def evaluate_model(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        """
        Evaluate regression model.
        
        Args:
            X_test: Test features
            y_test: Test target
            
        Returns:
            Dictionary of evaluation metrics
        """
        # Make predictions
        y_pred = self.model.predict(X_test)
        
        # Calculate metrics
        metrics = {
            'mse': mean_squared_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mae': mean_absolute_error(y_test, y_pred),
            'r2_score': r2_score(y_test, y_pred)
        }
        
        # Add MAPE if no zero values in y_test
        if not np.any(y_test == 0):
            try:
                metrics['mape'] = mean_absolute_percentage_error(y_test, y_pred)
            except Exception as e:
                logger.warning(f"Could not calculate MAPE: {e}")
        
        # Create residuals plot
        try:
            import matplotlib.pyplot as plt
            
            # Residuals plot
            residuals = y_test - y_pred
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # Predicted vs Actual
            ax1.scatter(y_test, y_pred, alpha=0.6)
            ax1.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
            ax1.set_xlabel('Actual')
            ax1.set_ylabel('Predicted')
            ax1.set_title('Predicted vs Actual')
            
            # Residuals plot
            ax2.scatter(y_pred, residuals, alpha=0.6)
            ax2.axhline(y=0, color='r', linestyle='--')
            ax2.set_xlabel('Predicted')
            ax2.set_ylabel('Residuals')
            ax2.set_title('Residuals Plot')
            
            plt.tight_layout()
            plt.savefig('regression_plots.png')
            mlflow.log_artifact('regression_plots.png')
            plt.close()
            
        except ImportError:
            logger.warning("matplotlib not available for plotting")
        
        logger.info(f"Model evaluation completed: {metrics}")
        
        return metrics
    
    def get_feature_importance(self) -> pd.DataFrame:
        """
        Get feature importance (if supported by the model).
        
        Returns:
            DataFrame with feature names and importance scores
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")
            
        if hasattr(self.model, 'feature_importances_'):
            # Tree-based models
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
        elif hasattr(self.model, 'coef_'):
            # Linear models
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'coefficient': self.model.coef_,
                'abs_coefficient': np.abs(self.model.coef_)
            }).sort_values('abs_coefficient', ascending=False)
            
        else:
            raise ValueError(f"{self.algorithm} does not support feature importance")
            
        return importance_df
    
    def predict_with_intervals(self, 
                              X: pd.DataFrame, 
                              confidence_level: float = 0.95) -> Dict:
        """
        Make predictions with prediction intervals (for tree-based models).
        
        Args:
            X: Input features
            confidence_level: Confidence level for intervals
            
        Returns:
            Dictionary with predictions and intervals
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")
            
        predictions = self.predict(X)
        
        result = {
            'predictions': predictions
        }
        
        # For RandomForest, we can estimate prediction intervals
        if self.algorithm == 'random_forest':
            # Get predictions from all trees
            tree_predictions = np.array([
                tree.predict(X) for tree in self.model.estimators_
            ])
            
            # Calculate percentiles for intervals
            alpha = 1 - confidence_level
            lower_percentile = (alpha / 2) * 100
            upper_percentile = (1 - alpha / 2) * 100
            
            result['lower_bound'] = np.percentile(tree_predictions, lower_percentile, axis=0)
            result['upper_bound'] = np.percentile(tree_predictions, upper_percentile, axis=0)
            result['prediction_std'] = np.std(tree_predictions, axis=0)
            
        return result
    
    def cross_validate(self, 
                      X: pd.DataFrame, 
                      y: pd.Series, 
                      cv: int = 5,
                      **model_params) -> Dict[str, float]:
        """
        Perform cross-validation.
        
        Args:
            X: Features
            y: Target
            cv: Number of cross-validation folds
            **model_params: Model parameters
            
        Returns:
            Cross-validation metrics
        """
        from sklearn.model_selection import cross_val_score
        
        # Create model
        model = self.create_model(**model_params)
        
        # Perform cross-validation
        cv_scores = {
            'cv_mse': -cross_val_score(model, X, y, cv=cv, scoring='neg_mean_squared_error'),
            'cv_mae': -cross_val_score(model, X, y, cv=cv, scoring='neg_mean_absolute_error'),
            'cv_r2': cross_val_score(model, X, y, cv=cv, scoring='r2')
        }
        
        # Calculate mean and std for each metric
        cv_results = {}
        for metric, scores in cv_scores.items():
            cv_results[f'{metric}_mean'] = np.mean(scores)
            cv_results[f'{metric}_std'] = np.std(scores)
            
        logger.info(f"Cross-validation completed: {cv_results}")
        
        return cv_results


# Example usage and training script
def train_regression_example():
    """Example function showing how to train a regression model."""
    from sklearn.datasets import make_regression
    
    # Generate sample data
    X, y = make_regression(
        n_samples=1000,
        n_features=20,
        n_informative=10,
        noise=0.1,
        random_state=42
    )
    
    # Convert to DataFrame
    feature_names = [f'feature_{i}' for i in range(X.shape[1])]
    data = pd.DataFrame(X, columns=feature_names)
    data['target'] = y
    
    # Initialize model
    model = RegressionModel(
        model_name="example_regressor",
        algorithm="random_forest"
    )
    
    # Prepare data
    X_train, X_test, y_train, y_test = model.prepare_data(data, 'target')
    
    # Train model
    metrics = model.train(
        X_train, y_train, X_test, y_test,
        n_estimators=50,
        max_depth=8
    )
    
    # Get feature importance
    importance = model.get_feature_importance()
    print("Top 5 most important features:")
    print(importance.head())
    
    # Make predictions with intervals
    predictions = model.predict_with_intervals(X_test.head())
    print(f"Predictions with intervals shape: {predictions['predictions'].shape}")
    
    # Cross-validation
    cv_results = model.cross_validate(X_train, y_train, cv=3)
    print(f"Cross-validation R2: {cv_results['cv_r2_mean']:.3f} ± {cv_results['cv_r2_std']:.3f}")
    
    return model, metrics


if __name__ == "__main__":
    # Run example
    model, metrics = train_regression_example()
    print(f"Training completed with metrics: {metrics}")