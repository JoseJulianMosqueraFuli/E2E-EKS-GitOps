"""
Test Models

Unit tests for ML models.
"""

import pytest
import pandas as pd
import numpy as np
from sklearn.datasets import make_classification, make_regression

from ..models.classification_model import ClassificationModel
from ..models.regression_model import RegressionModel


class TestClassificationModel:
    """Test classification model functionality."""
    
    @pytest.fixture
    def sample_classification_data(self):
        """Create sample classification data."""
        X, y = make_classification(
            n_samples=100,
            n_features=10,
            n_informative=5,
            n_classes=2,
            random_state=42
        )
        
        feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        data = pd.DataFrame(X, columns=feature_names)
        data['target'] = y
        
        return data
    
    def test_model_initialization(self):
        """Test model initialization."""
        model = ClassificationModel(
            model_name="test_classifier",
            algorithm="random_forest"
        )
        
        assert model.model_name == "test_classifier"
        assert model.algorithm == "random_forest"
        assert not model.is_trained
    
    def test_unsupported_algorithm(self):
        """Test error handling for unsupported algorithm."""
        with pytest.raises(ValueError):
            ClassificationModel(algorithm="unsupported_algorithm")
    
    def test_model_training(self, sample_classification_data):
        """Test model training."""
        model = ClassificationModel(
            model_name="test_classifier",
            algorithm="random_forest"
        )
        
        # Prepare data
        X_train, X_test, y_train, y_test = model.prepare_data(
            sample_classification_data, 'target'
        )
        
        # Train model
        metrics = model.train(
            X_train, y_train, X_test, y_test,
            n_estimators=10,  # Small for testing
            max_depth=3
        )
        
        assert model.is_trained
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 0 <= metrics['accuracy'] <= 1
    
    def test_predictions(self, sample_classification_data):
        """Test model predictions."""
        model = ClassificationModel(algorithm="random_forest")
        
        # Prepare and train
        X_train, X_test, y_train, y_test = model.prepare_data(
            sample_classification_data, 'target'
        )
        model.train(X_train, y_train, X_test, y_test, n_estimators=10)
        
        # Test predictions
        predictions = model.predict(X_test)
        assert len(predictions) == len(X_test)
        assert all(pred in [0, 1] for pred in predictions)
        
        # Test probability predictions
        probabilities = model.predict_proba(X_test)
        assert probabilities.shape == (len(X_test), 2)
        assert np.allclose(probabilities.sum(axis=1), 1.0)
    
    def test_feature_importance(self, sample_classification_data):
        """Test feature importance extraction."""
        model = ClassificationModel(algorithm="random_forest")
        
        # Prepare and train
        X_train, X_test, y_train, y_test = model.prepare_data(
            sample_classification_data, 'target'
        )
        model.train(X_train, y_train, X_test, y_test, n_estimators=10)
        
        # Get feature importance
        importance_df = model.get_feature_importance()
        
        assert len(importance_df) == len(model.feature_names)
        assert 'feature' in importance_df.columns
        assert 'importance' in importance_df.columns
        assert all(importance_df['importance'] >= 0)
    
    def test_predict_with_confidence(self, sample_classification_data):
        """Test predictions with confidence threshold."""
        model = ClassificationModel(algorithm="random_forest")
        
        # Prepare and train
        X_train, X_test, y_train, y_test = model.prepare_data(
            sample_classification_data, 'target'
        )
        model.train(X_train, y_train, X_test, y_test, n_estimators=10)
        
        # Test confident predictions
        results = model.predict_with_confidence(X_test, confidence_threshold=0.6)
        
        assert 'predictions' in results
        assert 'probabilities' in results
        assert 'is_confident' in results
        assert 'confident_predictions' in results
        assert len(results['predictions']) == len(X_test)


class TestRegressionModel:
    """Test regression model functionality."""
    
    @pytest.fixture
    def sample_regression_data(self):
        """Create sample regression data."""
        X, y = make_regression(
            n_samples=100,
            n_features=10,
            n_informative=5,
            noise=0.1,
            random_state=42
        )
        
        feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        data = pd.DataFrame(X, columns=feature_names)
        data['target'] = y
        
        return data
    
    def test_model_initialization(self):
        """Test model initialization."""
        model = RegressionModel(
            model_name="test_regressor",
            algorithm="random_forest"
        )
        
        assert model.model_name == "test_regressor"
        assert model.algorithm == "random_forest"
        assert not model.is_trained
    
    def test_model_training(self, sample_regression_data):
        """Test model training."""
        model = RegressionModel(
            model_name="test_regressor",
            algorithm="random_forest"
        )
        
        # Prepare data
        X_train, X_test, y_train, y_test = model.prepare_data(
            sample_regression_data, 'target'
        )
        
        # Train model
        metrics = model.train(
            X_train, y_train, X_test, y_test,
            n_estimators=10,  # Small for testing
            max_depth=3
        )
        
        assert model.is_trained
        assert 'mse' in metrics
        assert 'rmse' in metrics
        assert 'mae' in metrics
        assert 'r2_score' in metrics
        assert metrics['mse'] >= 0
        assert metrics['rmse'] >= 0
        assert metrics['mae'] >= 0
    
    def test_predictions(self, sample_regression_data):
        """Test model predictions."""
        model = RegressionModel(algorithm="random_forest")
        
        # Prepare and train
        X_train, X_test, y_train, y_test = model.prepare_data(
            sample_regression_data, 'target'
        )
        model.train(X_train, y_train, X_test, y_test, n_estimators=10)
        
        # Test predictions
        predictions = model.predict(X_test)
        assert len(predictions) == len(X_test)
        assert all(isinstance(pred, (int, float, np.number)) for pred in predictions)
    
    def test_predict_with_intervals(self, sample_regression_data):
        """Test predictions with intervals."""
        model = RegressionModel(algorithm="random_forest")
        
        # Prepare and train
        X_train, X_test, y_train, y_test = model.prepare_data(
            sample_regression_data, 'target'
        )
        model.train(X_train, y_train, X_test, y_test, n_estimators=10)
        
        # Test predictions with intervals
        results = model.predict_with_intervals(X_test)
        
        assert 'predictions' in results
        assert 'lower_bound' in results
        assert 'upper_bound' in results
        assert 'prediction_std' in results
        assert len(results['predictions']) == len(X_test)
        
        # Check that intervals make sense
        assert all(
            lower <= pred <= upper 
            for lower, pred, upper in zip(
                results['lower_bound'], 
                results['predictions'], 
                results['upper_bound']
            )
        )
    
    def test_cross_validation(self, sample_regression_data):
        """Test cross-validation."""
        model = RegressionModel(algorithm="random_forest")
        
        X = sample_regression_data.drop('target', axis=1)
        y = sample_regression_data['target']
        
        # Run cross-validation
        cv_results = model.cross_validate(
            X, y, cv=3, n_estimators=10
        )
        
        assert 'cv_mse_mean' in cv_results
        assert 'cv_mse_std' in cv_results
        assert 'cv_mae_mean' in cv_results
        assert 'cv_mae_std' in cv_results
        assert 'cv_r2_mean' in cv_results
        assert 'cv_r2_std' in cv_results
        
        assert cv_results['cv_mse_mean'] >= 0
        assert cv_results['cv_mae_mean'] >= 0


if __name__ == "__main__":
    pytest.main([__file__])