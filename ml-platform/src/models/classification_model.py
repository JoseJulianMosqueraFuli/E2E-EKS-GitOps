"""
Classification Model

Implementation of classification models with MLflow integration.
Supports multiple algorithms: RandomForest, XGBoost, LogisticRegression.
"""

import logging
from typing import Any, Dict
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix
)
import mlflow

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

from .base_model import BaseModel

logger = logging.getLogger(__name__)


class ClassificationModel(BaseModel):
    """Classification model with support for multiple algorithms."""
    
    SUPPORTED_ALGORITHMS = {
        'random_forest': RandomForestClassifier,
        'logistic_regression': LogisticRegression,
    }
    
    if XGBOOST_AVAILABLE:
        SUPPORTED_ALGORITHMS['xgboost'] = XGBClassifier
    
    def __init__(self, 
                 model_name: str = "classification_model",
                 algorithm: str = "random_forest",
                 experiment_name: str = "classification_experiments"):
        """
        Initialize classification model.
        
        Args:
            model_name: Name of the model
            algorithm: Algorithm to use ('random_forest', 'xgboost', 'logistic_regression')
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
        Create classification model instance.
        
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
            'logistic_regression': {
                'random_state': 42,
                'max_iter': 1000
            }
        }
        
        if XGBOOST_AVAILABLE:
            default_params['xgboost'] = {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'random_state': 42,
                'eval_metric': 'logloss'
            }
        
        # Merge default params with provided params
        params = default_params.get(self.algorithm, {})
        params.update(kwargs)
        
        logger.info(f"Creating {self.algorithm} model with params: {params}")
        
        return self.algorithm_class(**params)
    
    def evaluate_model(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        """
        Evaluate classification model.
        
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
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1_score': f1_score(y_test, y_pred, average='weighted')
        }
        
        # Add ROC AUC for binary classification
        if len(np.unique(y_test)) == 2:
            try:
                if hasattr(self.model, 'predict_proba'):
                    y_proba = self.model.predict_proba(X_test)[:, 1]
                    metrics['roc_auc'] = roc_auc_score(y_test, y_proba)
                else:
                    metrics['roc_auc'] = roc_auc_score(y_test, y_pred)
            except Exception as e:
                logger.warning(f"Could not calculate ROC AUC: {e}")
        
        # Log detailed classification report
        report = classification_report(y_test, y_pred, output_dict=True)
        
        # Log confusion matrix as artifact
        cm = confusion_matrix(y_test, y_pred)
        
        # Save classification report and confusion matrix as artifacts
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Plot confusion matrix
            plt.figure(figsize=(8, 6))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
            plt.title('Confusion Matrix')
            plt.ylabel('True Label')
            plt.xlabel('Predicted Label')
            plt.tight_layout()
            
            # Save plot
            plt.savefig('confusion_matrix.png')
            mlflow.log_artifact('confusion_matrix.png')
            plt.close()
            
        except ImportError:
            logger.warning("matplotlib/seaborn not available for plotting")
        
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
            
        if not hasattr(self.model, 'feature_importances_'):
            raise ValueError(f"{self.algorithm} does not support feature importance")
            
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return importance_df
    
    def predict_with_confidence(self, X: pd.DataFrame, confidence_threshold: float = 0.8) -> Dict:
        """
        Make predictions with confidence scores.
        
        Args:
            X: Input features
            confidence_threshold: Minimum confidence for prediction
            
        Returns:
            Dictionary with predictions, probabilities, and confidence flags
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")
            
        predictions = self.predict(X)
        
        result = {
            'predictions': predictions,
            'confident_predictions': predictions.copy()
        }
        
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.predict_proba(X)
            max_proba = np.max(probabilities, axis=1)
            
            result['probabilities'] = probabilities
            result['max_probability'] = max_proba
            result['is_confident'] = max_proba >= confidence_threshold
            
            # Set uncertain predictions to None or a special value
            result['confident_predictions'][max_proba < confidence_threshold] = -1
            
        return result


# Example usage and training script
def train_classification_example():
    """Example function showing how to train a classification model."""
    from sklearn.datasets import make_classification
    
    # Generate sample data
    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=10,
        n_redundant=10,
        n_classes=2,
        random_state=42
    )
    
    # Convert to DataFrame
    feature_names = [f'feature_{i}' for i in range(X.shape[1])]
    data = pd.DataFrame(X, columns=feature_names)
    data['target'] = y
    
    # Initialize model
    model = ClassificationModel(
        model_name="example_classifier",
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
    
    # Make predictions with confidence
    predictions = model.predict_with_confidence(X_test.head())
    print(f"Confident predictions: {np.sum(predictions['is_confident'])}/{len(predictions['predictions'])}")
    
    return model, metrics


if __name__ == "__main__":
    # Run example
    model, metrics = train_classification_example()
    print(f"Training completed with metrics: {metrics}")