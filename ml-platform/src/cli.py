"""
CLI Entry Point

Click-based CLI for the MLOps Platform.
Provides commands for training, inference, validation, and sample data generation.
"""

import os
import tempfile
import logging

import click
import pandas as pd

from src.utils.logging_config import setup_logging, MLOpsLogger
from src.utils.config_manager import ConfigManager
from src.pipelines.training_pipeline import TrainingPipeline
from src.pipelines.inference_pipeline import InferencePipeline
from src.data.data_loader import DataLoader
from src.data.data_validator import DataValidator

setup_logging()
logger = MLOpsLogger("cli")


@click.group()
def main():
    """MLOps Platform CLI - Training, inference, and data validation."""
    pass


@main.command("train")
@click.argument("data_path")
@click.option("--config-dir", default="config", help="Configuration directory")
@click.option("--config-name", default="config", help="Configuration file name")
@click.option("--environment", default="dev", help="Environment (dev/staging/prod)")
def train_cmd(data_path, config_dir, config_name, environment):
    """Train a machine learning model."""
    config_manager = ConfigManager(config_dir=config_dir, environment=environment)
    config = config_manager.load_config(config_name)

    if not config_manager.validate_config(config):
        raise click.ClickException("Invalid configuration")

    pipeline = TrainingPipeline()
    pipeline.config = config.__dict__
    results = pipeline.run_pipeline(data_path)

    click.echo(f"Training completed! Run ID: {results['run_id']}")
    click.echo(f"Test Metrics: {results['test_metrics']}")


@main.command("inference")
@click.argument("data_path")
@click.option("--model-uri", help="MLflow model URI")
@click.option("--model-path", help="Local model path")
@click.option("--feature-pipeline-path", help="Feature pipeline path")
@click.option("--output-path", help="Output path for predictions")
@click.option("--batch/--single", default=False, help="Batch or single inference")
@click.option("--batch-size", default=1000, type=int, help="Batch size")
@click.option("--return-probabilities", is_flag=True, help="Return probabilities")
@click.option("--confidence-threshold", default=0.8, type=float, help="Confidence threshold")
def inference_cmd(data_path, model_uri, model_path, feature_pipeline_path,
                  output_path, batch, batch_size, return_probabilities, confidence_threshold):
    """Run model inference."""
    inference_pipeline = InferencePipeline(
        model_uri=model_uri,
        model_path=model_path,
        feature_pipeline_path=feature_pipeline_path,
    )

    health = inference_pipeline.health_check()
    if health["status"] != "healthy":
        raise click.ClickException(f"Inference pipeline unhealthy: {health}")

    loader = DataLoader()

    if batch:
        results = inference_pipeline.predict_batch(
            data_path, output_path, batch_size=batch_size
        )
        click.echo(f"Batch inference completed: {results['num_samples']} predictions")
    else:
        data = loader.load_csv(data_path)
        results = inference_pipeline.predict(
            data,
            return_probabilities=return_probabilities,
            confidence_threshold=confidence_threshold,
        )
        click.echo(f"Inference completed: {results['num_samples']} predictions")
        if output_path:
            inference_pipeline.save_predictions_with_metadata(results, output_path)


@main.command("validate")
@click.argument("data_path")
@click.option("--suite-name", default="data_validation_suite", help="Expectation suite name")
@click.option("--create-suite", is_flag=True, help="Create new expectation suite")
def validate_cmd(data_path, suite_name, create_suite):
    """Validate data quality."""
    loader = DataLoader()
    data = loader.load_csv(data_path)

    validator = DataValidator()

    if create_suite:
        suite_name = validator.create_expectation_suite(
            suite_name, data.sample(min(1000, len(data))), overwrite=True
        )

    results = validator.validate_data(data, suite_name)

    click.echo(f"Data validation completed!")
    click.echo(f"Success: {results['success']}")
    click.echo(f"Success Rate: {results['success_percent']:.1f}%")
    click.echo(f"Report URL: {validator.get_validation_report_url()}")


@main.command("create-sample")
@click.argument("output_path")
@click.option("--n-samples", default=1000, type=int, help="Number of samples")
@click.option("--n-features", default=10, type=int, help="Number of features")
@click.option("--task-type", type=click.Choice(["classification", "regression"]),
              default="classification", help="Task type")
def create_sample_cmd(output_path, n_samples, n_features, task_type):
    """Create sample data for testing."""
    loader = DataLoader()
    data = loader.create_sample_data(
        n_samples=n_samples, n_features=n_features, task_type=task_type
    )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if output_path.endswith(".csv"):
        data.to_csv(output_path, index=False)
    elif output_path.endswith(".parquet"):
        data.to_parquet(output_path, index=False)
    else:
        raise click.ClickException("Output path must end with .csv or .parquet")

    click.echo(f"Created sample data: {data.shape}")
    click.echo(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()