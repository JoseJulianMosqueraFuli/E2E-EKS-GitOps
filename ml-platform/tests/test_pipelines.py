"""
Tests for the pipeline modules (TrainingPipeline and InferencePipeline).
"""

import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from src.pipelines.training_pipeline import TrainingPipeline
from src.pipelines.inference_pipeline import InferencePipeline


class TestTrainingPipelineInit:
    """Tests for TrainingPipeline initialization and structure."""

    @patch('src.pipelines.training_pipeline.mlflow')
    def test_instantiation_with_defaults(self, mock_mlflow):
        """Test TrainingPipeline can be instantiated with no config."""
        mock_mlflow.get_tracking_uri.return_value = "sqlite:///mlflow.db"
        pipeline = TrainingPipeline()
        assert pipeline is not None
        assert pipeline.config is not None
        assert isinstance(pipeline.config, dict)

    @patch('src.pipelines.training_pipeline.mlflow')
    def test_has_run_pipeline_method(self, mock_mlflow):
        """Test TrainingPipeline has the run_pipeline method."""
        mock_mlflow.get_tracking_uri.return_value = "sqlite:///mlflow.db"
        pipeline = TrainingPipeline()
        assert hasattr(pipeline, 'run_pipeline')
        assert callable(pipeline.run_pipeline)

    @patch('src.pipelines.training_pipeline.mlflow')
    def test_has_load_data_method(self, mock_mlflow):
        """Test TrainingPipeline has the load_data method."""
        mock_mlflow.get_tracking_uri.return_value = "sqlite:///mlflow.db"
        pipeline = TrainingPipeline()
        assert hasattr(pipeline, 'load_data')
        assert callable(pipeline.load_data)

    @patch('src.pipelines.training_pipeline.mlflow')
    def test_has_validate_data_method(self, mock_mlflow):
        """Test TrainingPipeline has the validate_data method."""
        mock_mlflow.get_tracking_uri.return_value = "sqlite:///mlflow.db"
        pipeline = TrainingPipeline()
        assert hasattr(pipeline, 'validate_data')
        assert callable(pipeline.validate_data)

    @patch('src.pipelines.training_pipeline.mlflow')
    def test_has_prepare_features_method(self, mock_mlflow):
        """Test TrainingPipeline has the prepare_features method."""
        mock_mlflow.get_tracking_uri.return_value = "sqlite:///mlflow.db"
        pipeline = TrainingPipeline()
        assert hasattr(pipeline, 'prepare_features')
        assert callable(pipeline.prepare_features)

    @patch('src.pipelines.training_pipeline.mlflow')
    def test_has_train_model_method(self, mock_mlflow):
        """Test TrainingPipeline has the train_model method."""
        mock_mlflow.get_tracking_uri.return_value = "sqlite:///mlflow.db"
        pipeline = TrainingPipeline()
        assert hasattr(pipeline, 'train_model')
        assert callable(pipeline.train_model)

    @patch('src.pipelines.training_pipeline.mlflow')
    def test_has_evaluate_model_method(self, mock_mlflow):
        """Test TrainingPipeline has the evaluate_model method."""
        mock_mlflow.get_tracking_uri.return_value = "sqlite:///mlflow.db"
        pipeline = TrainingPipeline()
        assert hasattr(pipeline, 'evaluate_model')
        assert callable(pipeline.evaluate_model)

    @patch('src.pipelines.training_pipeline.mlflow')
    def test_has_save_artifacts_method(self, mock_mlflow):
        """Test TrainingPipeline has the save_artifacts method."""
        mock_mlflow.get_tracking_uri.return_value = "sqlite:///mlflow.db"
        pipeline = TrainingPipeline()
        assert hasattr(pipeline, 'save_artifacts')
        assert callable(pipeline.save_artifacts)

    @patch('src.pipelines.training_pipeline.mlflow')
    def test_default_config_has_expected_keys(self, mock_mlflow):
        """Test the default config has the expected top-level keys."""
        mock_mlflow.get_tracking_uri.return_value = "sqlite:///mlflow.db"
        pipeline = TrainingPipeline()
        assert 'data' in pipeline.config
        assert 'model' in pipeline.config
        assert 'preprocessing' in pipeline.config
        assert 'mlflow' in pipeline.config


class TestInferencePipelineInit:
    """Tests for InferencePipeline initialization and structure."""

    def test_instantiation_without_model(self):
        """Test InferencePipeline can be instantiated with no model."""
        pipeline = InferencePipeline()
        assert pipeline is not None
        assert pipeline.model is None

    def test_has_predict_method(self):
        """Test InferencePipeline has the predict method."""
        pipeline = InferencePipeline()
        assert hasattr(pipeline, 'predict')
        assert callable(pipeline.predict)

    def test_has_predict_batch_method(self):
        """Test InferencePipeline has the predict_batch method."""
        pipeline = InferencePipeline()
        assert hasattr(pipeline, 'predict_batch')
        assert callable(pipeline.predict_batch)

    def test_has_load_model_from_mlflow_method(self):
        """Test InferencePipeline has the load_model_from_mlflow method."""
        pipeline = InferencePipeline()
        assert hasattr(pipeline, 'load_model_from_mlflow')
        assert callable(pipeline.load_model_from_mlflow)

    def test_has_load_model_from_path_method(self):
        """Test InferencePipeline has the load_model_from_path method."""
        pipeline = InferencePipeline()
        assert hasattr(pipeline, 'load_model_from_path')
        assert callable(pipeline.load_model_from_path)

    def test_has_health_check_method(self):
        """Test InferencePipeline has the health_check method."""
        pipeline = InferencePipeline()
        assert hasattr(pipeline, 'health_check')
        assert callable(pipeline.health_check)

    def test_has_preprocess_data_method(self):
        """Test InferencePipeline has the preprocess_data method."""
        pipeline = InferencePipeline()
        assert hasattr(pipeline, 'preprocess_data')
        assert callable(pipeline.preprocess_data)

    def test_has_get_inference_stats_method(self):
        """Test InferencePipeline has the get_inference_stats method."""
        pipeline = InferencePipeline()
        assert hasattr(pipeline, 'get_inference_stats')
        assert callable(pipeline.get_inference_stats)

    def test_initial_inference_stats(self):
        """Test InferencePipeline has correct initial statistics."""
        pipeline = InferencePipeline()
        stats = pipeline.get_inference_stats()
        assert stats['total_predictions'] == 0
        assert stats['total_inference_time'] == 0.0
        assert stats['error_count'] == 0

    def test_health_check_without_model(self):
        """Test health_check works when no model is loaded."""
        pipeline = InferencePipeline()
        health = pipeline.health_check()
        assert health['model_loaded'] is False
        assert health['feature_pipeline_loaded'] is False
        # Status is healthy because no model means no test prediction failure
        assert 'status' in health


class TestInferencePipelinePredict:
    """Tests for InferencePipeline predict behavior."""

    def test_predict_raises_without_model(self):
        """Test that predict raises ValueError when no model is loaded."""
        pipeline = InferencePipeline()
        data = pd.DataFrame(np.random.randn(5, 3), columns=['a', 'b', 'c'])
        with pytest.raises(ValueError, match="No model loaded"):
            pipeline.predict(data)

    def test_predict_with_mock_model(self):
        """Test predict works with a mock model."""
        pipeline = InferencePipeline()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0, 1, 0, 1, 0])
        pipeline.model = mock_model

        data = pd.DataFrame(np.random.randn(5, 3), columns=['a', 'b', 'c'])
        result = pipeline.predict(data)

        assert result['num_samples'] == 5
        assert len(result['predictions']) == 5
        assert 'inference_time' in result
        mock_model.predict.assert_called_once()

    def test_predict_updates_stats(self):
        """Test that predict updates inference statistics."""
        pipeline = InferencePipeline()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1, 0, 1])
        pipeline.model = mock_model

        data = pd.DataFrame(np.random.randn(3, 2), columns=['x', 'y'])
        pipeline.predict(data)

        stats = pipeline.get_inference_stats()
        assert stats['total_predictions'] == 3
        assert stats['total_inference_time'] > 0

    def test_reset_stats(self):
        """Test that reset_stats clears the statistics."""
        pipeline = InferencePipeline()
        pipeline.inference_stats['total_predictions'] = 100
        pipeline.reset_stats()
        stats = pipeline.get_inference_stats()
        assert stats['total_predictions'] == 0
