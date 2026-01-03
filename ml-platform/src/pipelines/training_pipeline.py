"""
Training Pipeline

End-to-end ML training pipeline with data validation, feature engineering,
model training, and MLflow tracking.
"""

import logging
import os
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from datetime import datetime
import yaml

from ..data.data_loader import DataLoader
from ..data.data_validator import DataValidator
from ..data.feature_engineering import FeatureEngineer
from ..models.classification_model import ClassificationModel
from ..models.regression_model import RegressionModel

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """End-to-end ML training pipeline."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize training pipeline.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.data_loader = DataLoader(
            aws_region=self.config.get('aws_region', 'us-west-2'),
            s3_bucket=self.config.get('s3_bucket')
        )
        self.data_validator = DataValidator()
        self.feature_engineer = FeatureEngineer()
        self.model = None
        
        # Setup MLflow
        mlflow_config = self.config.get('mlflow', {})
        if mlflow_config.get('tracking_uri'):
            mlflow.set_tracking_uri(mlflow_config['tracking_uri'])
        
        self.experiment_name = mlflow_config.get('experiment_name', 'default_experiment')
        mlflow.set_experiment(self.experiment_name)
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded config from {config_path}")
        else:
            # Default configuration
            config = {
                'data': {
                    'source': 'local',
                    'format': 'csv',
                    'target_column': 'target',
                    'test_size': 0.2,
                    'validation_size': 0.1
                },
                'preprocessing': {
                    'numeric_strategy': 'standard',
                    'categorical_strategy': 'onehot',
                    'handle_outliers': True,
                    'feature_selection': {
                        'enabled': True,
                        'method': 'k_best',
                        'k': 10
                    }
                },
                'model': {
                    'type': 'classification',
                    'algorithm': 'random_forest',
                    'hyperparameters': {
                        'n_estimators': 100,
                        'max_depth': 10,
                        'random_state': 42
                    }
                },
                'validation': {
                    'enabled': True,
                    'create_suite': True
                },
                'mlflow': {
                    'experiment_name': 'training_pipeline',
                    'run_name_prefix': 'pipeline_run'
                }
            }
            logger.info("Using default configuration")
            
        return config
    
    def load_data(self, data_path: str) -> pd.DataFrame:
        """
        Load data from specified path.
        
        Args:
            data_path: Path to data file
            
        Returns:
            Loaded DataFrame
        """
        data_config = self.config['data']
        
        if data_config['format'] == 'csv':
            data = self.data_loader.load_csv(
                data_path, 
                source=data_config['source']
            )
        elif data_config['format'] == 'parquet':
            data = self.data_loader.load_parquet(
                data_path,
                source=data_config['source']
            )
        elif data_config['format'] == 'json':
            data = self.data_loader.load_json(
                data_path,
                source=data_config['source']
            )
        else:
            raise ValueError(f"Unsupported format: {data_config['format']}")
        
        logger.info(f"Loaded data: {data.shape}")
        return data
    
    def validate_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate data quality.
        
        Args:
            data: Input data
            
        Returns:
            Validation results
        """
        validation_config = self.config['validation']
        
        if not validation_config.get('enabled', True):
            logger.info("Data validation disabled")
            return {'success': True, 'message': 'Validation skipped'}
        
        # Create expectation suite if needed
        suite_name = f"{self.experiment_name}_data_validation"
        
        if validation_config.get('create_suite', True):
            self.data_validator.create_expectation_suite(
                suite_name,
                data.sample(min(1000, len(data))),  # Use sample for profiling
                overwrite=True
            )
        
        # Validate data
        results = self.data_validator.validate_data(data, suite_name)
        
        # Log validation results to MLflow
        mlflow.log_metrics({
            'data_validation_success': int(results['success']),
            'data_validation_success_percent': results['success_percent']
        })
        
        return results
    
    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, pd.Series, List[str]]:
        """
        Prepare features using feature engineering pipeline.
        
        Args:
            data: Input data
            
        Returns:
            Tuple of (features, target, feature_names)
        """
        preprocessing_config = self.config['preprocessing']
        target_column = self.config['data']['target_column']
        
        # Separate features and target
        X = data.drop(columns=[target_column])
        y = data[target_column]
        
        # Identify feature types
        numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
        categorical_features = X.select_dtypes(include=['object', 'category']).columns.tolist()
        
        logger.info(f"Numeric features: {len(numeric_features)}")
        logger.info(f"Categorical features: {len(categorical_features)}")
        
        # Create preprocessor
        self.feature_engineer.create_preprocessor(
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            numeric_strategy=preprocessing_config['numeric_strategy'],
            categorical_strategy=preprocessing_config['categorical_strategy']
        )
        
        # Fit and transform features
        X_transformed = self.feature_engineer.fit_transform(X)
        
        # Feature selection
        feature_selection_config = preprocessing_config.get('feature_selection', {})
        if feature_selection_config.get('enabled', False):
            task_type = self.config['model']['type']
            X_transformed = self.feature_engineer.select_features(
                X_transformed,
                y,
                method=feature_selection_config.get('method', 'k_best'),
                k=feature_selection_config.get('k', 10),
                task_type=task_type
            )
        
        # Get feature names
        feature_names = self.feature_engineer.get_selected_feature_names()
        
        logger.info(f"Final feature shape: {X_transformed.shape}")
        
        return X_transformed, y, feature_names
    
    def split_data(self, X: np.ndarray, y: pd.Series) -> Tuple[np.ndarray, np.ndarray, np.ndarray, pd.Series, pd.Series, pd.Series]:
        """
        Split data into train, validation, and test sets.
        
        Args:
            X: Features
            y: Target
            
        Returns:
            X_train, X_val, X_test, y_train, y_val, y_test
        """
        from sklearn.model_selection import train_test_split
        
        data_config = self.config['data']
        test_size = data_config.get('test_size', 0.2)
        val_size = data_config.get('validation_size', 0.1)
        
        # First split: separate test set
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y if self.config['model']['type'] == 'classification' else None
        )
        
        # Second split: separate train and validation
        val_size_adjusted = val_size / (1 - test_size)  # Adjust for remaining data
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_size_adjusted, random_state=42, 
            stratify=y_temp if self.config['model']['type'] == 'classification' else None
        )
        
        logger.info(f"Data split - Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")
        
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def train_model(self, X_train: np.ndarray, y_train: pd.Series, X_val: np.ndarray, y_val: pd.Series) -> Dict[str, float]:
        """
        Train the ML model.
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
            
        Returns:
            Training metrics
        """
        model_config = self.config['model']
        
        # Initialize model
        if model_config['type'] == 'classification':
            self.model = ClassificationModel(
                model_name=f"{self.experiment_name}_classifier",
                algorithm=model_config['algorithm'],
                experiment_name=self.experiment_name
            )
        elif model_config['type'] == 'regression':
            self.model = RegressionModel(
                model_name=f"{self.experiment_name}_regressor",
                algorithm=model_config['algorithm'],
                experiment_name=self.experiment_name
            )
        else:
            raise ValueError(f"Unsupported model type: {model_config['type']}")
        
        # Convert numpy arrays to DataFrames for model compatibility
        feature_names = self.feature_engineer.get_selected_feature_names()
        X_train_df = pd.DataFrame(X_train, columns=feature_names)
        X_val_df = pd.DataFrame(X_val, columns=feature_names)
        
        # Train model
        metrics = self.model.train(
            X_train_df, y_train, X_val_df, y_val,
            **model_config.get('hyperparameters', {})
        )
        
        return metrics
    
    def evaluate_model(self, X_test: np.ndarray, y_test: pd.Series) -> Dict[str, float]:
        """
        Evaluate model on test set.
        
        Args:
            X_test: Test features
            y_test: Test target
            
        Returns:
            Test metrics
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        # Convert to DataFrame
        feature_names = self.feature_engineer.get_selected_feature_names()
        X_test_df = pd.DataFrame(X_test, columns=feature_names)
        
        # Evaluate
        test_metrics = self.model.evaluate_model(X_test_df, y_test)
        
        # Log test metrics with prefix
        test_metrics_prefixed = {f"test_{k}": v for k, v in test_metrics.items()}
        mlflow.log_metrics(test_metrics_prefixed)
        
        return test_metrics
    
    def save_artifacts(self, run_id: str):
        """
        Save pipeline artifacts.
        
        Args:
            run_id: MLflow run ID
        """
        # Save feature engineering pipeline
        fe_path = f"artifacts/feature_pipeline_{run_id}.joblib"
        self.feature_engineer.save_pipeline(fe_path)
        mlflow.log_artifact(fe_path)
        
        # Save model separately (already logged by model.train())
        if self.model:
            model_path = f"artifacts/model_{run_id}.joblib"
            self.model.save_model(model_path)
            mlflow.log_artifact(model_path)
        
        # Save configuration
        config_path = f"artifacts/config_{run_id}.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(self.config, f)
        mlflow.log_artifact(config_path)
        
        logger.info(f"Saved artifacts for run {run_id}")
    
    def run_pipeline(self, data_path: str) -> Dict[str, Any]:
        """
        Run the complete training pipeline.
        
        Args:
            data_path: Path to training data
            
        Returns:
            Pipeline results
        """
        run_name = f"{self.config['mlflow'].get('run_name_prefix', 'pipeline')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with mlflow.start_run(run_name=run_name) as run:
            try:
                # Log configuration
                mlflow.log_params(self._flatten_config(self.config))
                
                # Step 1: Load data
                logger.info("Step 1: Loading data...")
                data = self.load_data(data_path)
                mlflow.log_metric("data_samples", len(data))
                mlflow.log_metric("data_features", len(data.columns) - 1)
                
                # Step 2: Validate data
                logger.info("Step 2: Validating data...")
                validation_results = self.validate_data(data)
                
                if not validation_results['success']:
                    logger.warning(f"Data validation failed: {validation_results}")
                
                # Step 3: Feature engineering
                logger.info("Step 3: Feature engineering...")
                X, y, feature_names = self.prepare_features(data)
                mlflow.log_metric("final_features", X.shape[1])
                
                # Step 4: Split data
                logger.info("Step 4: Splitting data...")
                X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(X, y)
                
                # Step 5: Train model
                logger.info("Step 5: Training model...")
                train_metrics = self.train_model(X_train, y_train, X_val, y_val)
                
                # Step 6: Evaluate on test set
                logger.info("Step 6: Evaluating model...")
                test_metrics = self.evaluate_model(X_test, y_test)
                
                # Step 7: Save artifacts
                logger.info("Step 7: Saving artifacts...")
                self.save_artifacts(run.info.run_id)
                
                # Prepare results
                results = {
                    'run_id': run.info.run_id,
                    'experiment_name': self.experiment_name,
                    'data_validation': validation_results,
                    'train_metrics': train_metrics,
                    'test_metrics': test_metrics,
                    'feature_names': feature_names,
                    'model_type': self.config['model']['type'],
                    'model_algorithm': self.config['model']['algorithm']
                }
                
                logger.info("Pipeline completed successfully!")
                return results
                
            except Exception as e:
                logger.error(f"Pipeline failed: {e}")
                mlflow.log_param("pipeline_status", "failed")
                mlflow.log_param("error_message", str(e))
                raise
    
    def _flatten_config(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested configuration for MLflow logging."""
        flat_config = {}
        
        for key, value in config.items():
            new_key = f"{prefix}{key}" if prefix else key
            
            if isinstance(value, dict):
                flat_config.update(self._flatten_config(value, f"{new_key}_"))
            else:
                flat_config[new_key] = value
                
        return flat_config


# Example usage
def run_training_example():
    """Example of running the training pipeline."""
    # Create sample data
    loader = DataLoader()
    sample_data = loader.create_sample_data(
        n_samples=1000,
        n_features=10,
        task_type="classification"
    )
    
    # Save sample data
    os.makedirs("data", exist_ok=True)
    sample_data.to_csv("data/sample_training_data.csv", index=False)
    
    # Create configuration
    config = {
        'data': {
            'source': 'local',
            'format': 'csv',
            'target_column': 'target',
            'test_size': 0.2,
            'validation_size': 0.1
        },
        'model': {
            'type': 'classification',
            'algorithm': 'random_forest',
            'hyperparameters': {
                'n_estimators': 50,
                'max_depth': 8,
                'random_state': 42
            }
        },
        'preprocessing': {
            'feature_selection': {
                'enabled': True,
                'method': 'k_best',
                'k': 8
            }
        }
    }
    
    # Save configuration
    with open("config/training_config.yaml", "w") as f:
        yaml.dump(config, f)
    
    # Initialize and run pipeline
    pipeline = TrainingPipeline("config/training_config.yaml")
    results = pipeline.run_pipeline("data/sample_training_data.csv")
    
    print(f"Pipeline completed!")
    print(f"Run ID: {results['run_id']}")
    print(f"Test metrics: {results['test_metrics']}")
    
    return pipeline, results


if __name__ == "__main__":
    # Create directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    os.makedirs("artifacts", exist_ok=True)
    
    # Run example
    pipeline, results = run_training_example()