"""
Integration tests for end-to-end MLOps pipelines.

These tests exercise the full training and inference pipelines
without requiring external services (AWS, MLflow server, etc.).
"""

import os
import tempfile
import pytest

from src.pipelines.training_pipeline import TrainingPipeline
from src.pipelines.inference_pipeline import InferencePipeline


class TestTrainingPipelineIntegration:
    """Integration tests for the training pipeline."""

    def test_pipeline_runs_successfully(
        self, sample_classification_data, temp_project_dir, mock_mlflow_tracking_uri
    ):
        """End-to-end: train a model and verify artifacts are produced."""
        data_path = os.path.join(temp_project_dir, 'data', 'train.csv')
        sample_classification_data.to_csv(data_path, index=False)

        config_path = os.path.join(temp_project_dir, 'config', 'train.yaml')
        pipeline = TrainingPipeline(config_path=config_path)
        results = pipeline.run_pipeline(data_path)

        assert 'run_id' in results
        assert 'test_metrics' in results
        assert results['model_type'] == 'classification'
        assert os.path.exists(data_path)

    def test_pipeline_with_validation(
        self, sample_classification_data, temp_project_dir, mock_mlflow_tracking_uri
    ):
        """Pipeline with data validation enabled should still complete."""
        data_path = os.path.join(temp_project_dir, 'data', 'train.csv')
        sample_classification_data.to_csv(data_path, index=False)

        config_path = os.path.join(temp_project_dir, 'config', 'train.yaml')
        pipeline = TrainingPipeline(config_path=config_path)
        results = pipeline.run_pipeline(data_path)

        assert results['data_validation']['success'] is True


class TestInferencePipelineIntegration:
    """Integration tests for the inference pipeline."""

    def test_inference_after_training(
        self, sample_classification_data, temp_project_dir, mock_mlflow_tracking_uri
    ):
        """Train a model and then run inference on the same data format."""
        data_path = os.path.join(temp_project_dir, 'data', 'train.csv')
        sample_classification_data.to_csv(data_path, index=False)

        # Train
        train_pipeline = TrainingPipeline()
        train_results = train_pipeline.run_pipeline(data_path)

        # Save model locally for inference
        model_path = os.path.join(temp_project_dir, 'models', 'model.joblib')
        train_pipeline.model.save_model(model_path)

        # Inference
        inf_pipeline = InferencePipeline(
            model_path=model_path,
            feature_pipeline_path=None
        )
        predictions = inf_pipeline.predict(
            sample_classification_data.drop(columns=['target'])
        )

        assert predictions is not None
        assert len(predictions) == len(sample_classification_data)

    def test_batch_inference(
        self, sample_classification_data, temp_project_dir, mock_mlflow_tracking_uri
    ):
        """Run batch inference and write predictions to disk."""
        data_path = os.path.join(temp_project_dir, 'data', 'train.csv')
        output_path = os.path.join(temp_project_dir, 'data', 'predictions.json')
        sample_classification_data.to_csv(data_path, index=False)

        train_pipeline = TrainingPipeline()
        train_pipeline.run_pipeline(data_path)

        model_path = os.path.join(temp_project_dir, 'models', 'model.joblib')
        train_pipeline.model.save_model(model_path)

        inf_pipeline = InferencePipeline(model_path=model_path)
        results = inf_pipeline.predict_batch(data_path, output_path, batch_size=50)

        assert results['num_samples'] == len(sample_classification_data)
        assert os.path.exists(output_path)
