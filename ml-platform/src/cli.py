"""
CLI Entry Point

Click-based CLI for the MLOps Platform.
Provides commands for training, inference, validation, and sample data generation.
"""

import json
import os

import click

from src.data.data_loader import DataLoader
from src.data.data_validator import DataValidator
from src.pipelines import steps
from src.pipelines.inference_pipeline import InferencePipeline
from src.pipelines.training_pipeline import TrainingPipeline
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import MLOpsLogger, setup_logging

setup_logging()
logger = MLOpsLogger("cli")


@click.group()
def main():
    """MLOps Platform CLI - Training, inference, and data validation."""


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
def inference_cmd(
    data_path,
    model_uri,
    model_path,
    feature_pipeline_path,
    output_path,
    batch,
    batch_size,
    return_probabilities,
    confidence_threshold,
):
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
        results = inference_pipeline.predict_batch(data_path, output_path, batch_size=batch_size)
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

    click.echo("Data validation completed!")
    click.echo(f"Success: {results['success']}")
    click.echo(f"Success Rate: {results['success_percent']:.1f}%")
    click.echo(f"Report URL: {validator.get_validation_report_url()}")


@main.command("create-sample")
@click.argument("output_path")
@click.option("--n-samples", default=1000, type=int, help="Number of samples")
@click.option("--n-features", default=10, type=int, help="Number of features")
@click.option(
    "--task-type",
    type=click.Choice(["classification", "regression"]),
    default="classification",
    help="Task type",
)
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


TASK_TYPE_OPTION = click.option(
    "--task-type",
    type=click.Choice(list(steps.TASK_TYPES)),
    default="classification",
    help="Task type",
)
TARGET_OPTION = click.option("--target", default="target", help="Target column")
OUTPUTS_DIR_OPTION = click.option(
    "--outputs-dir", default="/tmp", help="Directory for Argo output parameter files"
)


@main.group("step")
def step():
    """Single pipeline steps, one per container (used by Argo Workflows)."""


@step.command("split")
@click.option("--input", "input_uri", required=True, help="Raw data URI (.csv/.parquet)")
@click.option("--output", "output_prefix", required=True, help="Output prefix URI")
@TARGET_OPTION
@TASK_TYPE_OPTION
@click.option("--test-size", default=0.2, type=float, help="Test fraction")
@OUTPUTS_DIR_OPTION
def step_split_cmd(input_uri, output_prefix, target, task_type, test_size, outputs_dir):
    """Split raw data into train and test sets."""
    train_uri, test_uri = steps.split_dataset(
        input_uri, output_prefix, target, task_type, test_size=test_size
    )
    steps.write_outputs(
        outputs_dir, {"features-path.txt": train_uri, "test-data-path.txt": test_uri}
    )
    click.echo(f"train={train_uri} test={test_uri}")


@step.command("train")
@click.option("--features", "train_uri", required=True, help="Training data URI")
@click.option("--model-name", required=True, help="Registered model name")
@click.option("--experiment-name", required=True, help="MLflow experiment name")
@TARGET_OPTION
@TASK_TYPE_OPTION
@click.option("--algorithm", default="random_forest", help="Algorithm name")
@click.option("--params", default="{}", help="Hyperparameters as JSON")
@OUTPUTS_DIR_OPTION
def step_train_cmd(
    train_uri, model_name, experiment_name, target, task_type, algorithm, params, outputs_dir
):
    """Train a model pipeline and log it to MLflow."""
    model_uri, run_id = steps.train(
        train_uri,
        model_name,
        experiment_name,
        target,
        task_type,
        algorithm=algorithm,
        params=json.loads(params),
    )
    steps.write_outputs(outputs_dir, {"model-uri.txt": model_uri, "run-id.txt": run_id})
    click.echo(f"model_uri={model_uri}")


@step.command("evaluate")
@click.option("--model-uri", required=True, help="Candidate model URI")
@click.option("--test-data", "test_uri", required=True, help="Test data URI")
@click.option("--model-name", required=True, help="Registered model name")
@TARGET_OPTION
@TASK_TYPE_OPTION
@click.option("--min-score", default=0.0, type=float, help="Minimum primary metric")
@click.option("--min-improvement", default=0.0, type=float, help="Required gain over champion")
@click.option("--alias", default="champion", help="Alias of the model to beat")
@OUTPUTS_DIR_OPTION
def step_evaluate_cmd(
    model_uri,
    test_uri,
    model_name,
    target,
    task_type,
    min_score,
    min_improvement,
    alias,
    outputs_dir,
):
    """Evaluate a candidate and decide whether it can be promoted."""
    report = steps.evaluate(
        model_uri,
        test_uri,
        model_name,
        target,
        task_type,
        min_score=min_score,
        min_improvement=min_improvement,
        alias=alias,
    )
    steps.write_outputs(
        outputs_dir,
        {
            "model-approved.txt": str(report["approved"]).lower(),
            "evaluation-metrics.json": json.dumps(report),
        },
    )
    click.echo(f"approved={report['approved']} reasons={report['reasons']}")


@step.command("register")
@click.option("--model-uri", required=True, help="Approved model URI")
@click.option("--model-name", required=True, help="Registered model name")
@click.option("--alias", default="champion", help="Alias to assign")
@OUTPUTS_DIR_OPTION
def step_register_cmd(model_uri, model_name, alias, outputs_dir):
    """Register an approved model and assign an alias."""
    version = steps.register(model_uri, model_name, alias=alias)
    steps.write_outputs(outputs_dir, {"model-version.txt": version})
    click.echo(f"version={version}")


if __name__ == "__main__":
    main()
