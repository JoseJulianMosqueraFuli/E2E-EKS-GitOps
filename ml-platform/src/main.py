"""
Main Entry Point

Main script for running MLOps platform operations including training,
inference, and data validation.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from utils.logging_config import setup_logging, MLOpsLogger
from utils.config_manager import ConfigManager
from pipelines.training_pipeline import TrainingPipeline
from pipelines.inference_pipeline import InferencePipeline
from data.data_loader import DataLoader
from data.data_validator import DataValidator

# Setup logging
setup_logging()
logger = MLOpsLogger("main")


def train_model(args):
    """Train a machine learning model."""
    logger.log_pipeline_step("train_start", "started", 0)
    
    try:
        # Load configuration
        config_manager = ConfigManager(
            config_dir=args.config_dir,
            environment=args.environment
        )
        config = config_manager.load_config(args.config_name)
        
        # Validate configuration
        if not config_manager.validate_config(config):
            raise ValueError("Invalid configuration")
        
        # Initialize training pipeline
        pipeline = TrainingPipeline()
        pipeline.config = config.__dict__
        
        # Run training
        results = pipeline.run_pipeline(args.data_path)
        
        logger.log_pipeline_step("train_complete", "completed", 0, {
            "run_id": results["run_id"],
            "test_metrics": results["test_metrics"]
        })
        
        print(f"Training completed successfully!")
        print(f"Run ID: {results['run_id']}")
        print(f"Test Metrics: {results['test_metrics']}")
        
        return results
        
    except Exception as e:
        logger.log_error(e, {"operation": "train_model"})
        raise


def run_inference(args):
    """Run model inference."""
    logger.log_pipeline_step("inference_start", "started", 0)
    
    try:
        # Initialize inference pipeline
        inference_pipeline = InferencePipeline(
            model_uri=args.model_uri,
            model_path=args.model_path,
            feature_pipeline_path=args.feature_pipeline_path
        )
        
        # Health check
        health = inference_pipeline.health_check()
        if health['status'] != 'healthy':
            raise ValueError(f"Inference pipeline unhealthy: {health}")
        
        # Run inference
        if args.batch_inference:
            results = inference_pipeline.predict_batch(
                args.data_path,
                args.output_path,
                batch_size=args.batch_size
            )
            print(f"Batch inference completed: {results['num_samples']} predictions")
        else:
            # Load data for single inference
            loader = DataLoader()
            data = loader.load_csv(args.data_path)
            
            results = inference_pipeline.predict(
                data,
                return_probabilities=args.return_probabilities,
                confidence_threshold=args.confidence_threshold
            )
            
            print(f"Inference completed: {results['num_samples']} predictions")
            
            # Save results if output path specified
            if args.output_path:
                inference_pipeline.save_predictions_with_metadata(
                    results, args.output_path
                )
        
        logger.log_pipeline_step("inference_complete", "completed", 0, {
            "num_predictions": results["num_samples"]
        })
        
        return results
        
    except Exception as e:
        logger.log_error(e, {"operation": "run_inference"})
        raise


def validate_data(args):
    """Validate data quality."""
    logger.log_pipeline_step("validation_start", "started", 0)
    
    try:
        # Load data
        loader = DataLoader()
        data = loader.load_csv(args.data_path)
        
        # Initialize validator
        validator = DataValidator()
        
        # Create or use existing expectation suite
        if args.create_suite:
            suite_name = validator.create_expectation_suite(
                args.suite_name or "data_validation_suite",
                data.sample(min(1000, len(data))),
                overwrite=True
            )
        else:
            suite_name = args.suite_name or "data_validation_suite"
        
        # Run validation
        results = validator.validate_data(data, suite_name)
        
        logger.log_pipeline_step("validation_complete", "completed", 0, {
            "success": results["success"],
            "success_percent": results["success_percent"]
        })
        
        print(f"Data validation completed!")
        print(f"Success: {results['success']}")
        print(f"Success Rate: {results['success_percent']:.1f}%")
        print(f"Report URL: {validator.get_validation_report_url()}")
        
        return results
        
    except Exception as e:
        logger.log_error(e, {"operation": "validate_data"})
        raise


def create_sample_data(args):
    """Create sample data for testing."""
    try:
        loader = DataLoader()
        
        # Create sample data
        data = loader.create_sample_data(
            n_samples=args.n_samples,
            n_features=args.n_features,
            task_type=args.task_type
        )
        
        # Save data
        os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
        
        if args.output_path.endswith('.csv'):
            data.to_csv(args.output_path, index=False)
        elif args.output_path.endswith('.parquet'):
            data.to_parquet(args.output_path, index=False)
        else:
            raise ValueError("Output path must end with .csv or .parquet")
        
        print(f"Created sample data: {data.shape}")
        print(f"Saved to: {args.output_path}")
        
        return data
        
    except Exception as e:
        logger.log_error(e, {"operation": "create_sample_data"})
        raise


def setup_project(args):
    """Setup project structure and configuration."""
    try:
        # Create directories
        directories = [
            "data", "config", "logs", "artifacts", "models", "notebooks"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        
        # Create configuration files
        config_manager = ConfigManager(environment=args.environment)
        config_manager.create_default_configs()
        
        # Create logging configuration
        from utils.logging_config import create_logging_config_file
        create_logging_config_file()
        
        # Create sample data
        loader = DataLoader()
        sample_data = loader.create_sample_data(
            n_samples=1000,
            n_features=10,
            task_type="classification"
        )
        sample_data.to_csv("data/sample_data.csv", index=False)
        
        print("Project setup completed!")
        print("Created:")
        print("- Configuration files in config/")
        print("- Logging configuration")
        print("- Sample data in data/sample_data.csv")
        print("- Directory structure")
        
    except Exception as e:
        logger.log_error(e, {"operation": "setup_project"})
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MLOps Platform CLI")
    
    # Global arguments
    parser.add_argument("--config-dir", default="config", help="Configuration directory")
    parser.add_argument("--config-name", default="config", help="Configuration file name")
    parser.add_argument("--environment", default="dev", help="Environment (dev/staging/prod)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Train command
    train_parser = subparsers.add_parser("train", help="Train a model")
    train_parser.add_argument("data_path", help="Path to training data")
    train_parser.set_defaults(func=train_model)
    
    # Inference command
    inference_parser = subparsers.add_parser("inference", help="Run model inference")
    inference_parser.add_argument("data_path", help="Path to input data")
    inference_parser.add_argument("--model-uri", help="MLflow model URI")
    inference_parser.add_argument("--model-path", help="Local model path")
    inference_parser.add_argument("--feature-pipeline-path", help="Feature pipeline path")
    inference_parser.add_argument("--output-path", help="Output path for predictions")
    inference_parser.add_argument("--batch-inference", action="store_true", help="Run batch inference")
    inference_parser.add_argument("--batch-size", type=int, default=1000, help="Batch size")
    inference_parser.add_argument("--return-probabilities", action="store_true", help="Return probabilities")
    inference_parser.add_argument("--confidence-threshold", type=float, default=0.8, help="Confidence threshold")
    inference_parser.set_defaults(func=run_inference)
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate data quality")
    validate_parser.add_argument("data_path", help="Path to data to validate")
    validate_parser.add_argument("--suite-name", help="Expectation suite name")
    validate_parser.add_argument("--create-suite", action="store_true", help="Create new expectation suite")
    validate_parser.set_defaults(func=validate_data)
    
    # Create sample data command
    sample_parser = subparsers.add_parser("create-sample", help="Create sample data")
    sample_parser.add_argument("output_path", help="Output path for sample data")
    sample_parser.add_argument("--n-samples", type=int, default=1000, help="Number of samples")
    sample_parser.add_argument("--n-features", type=int, default=10, help="Number of features")
    sample_parser.add_argument("--task-type", choices=["classification", "regression"], 
                              default="classification", help="Task type")
    sample_parser.set_defaults(func=create_sample_data)
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Setup project structure")
    setup_parser.set_defaults(func=setup_project)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run command
    if hasattr(args, 'func'):
        try:
            args.func(args)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()