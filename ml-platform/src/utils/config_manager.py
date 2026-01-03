"""
Configuration Manager

Centralized configuration management for the MLOps platform.
Supports environment-specific configs, validation, and secrets management.
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DataConfig:
    """Data configuration."""
    source: str = "local"
    format: str = "csv"
    target_column: str = "target"
    test_size: float = 0.2
    validation_size: float = 0.1
    s3_bucket: Optional[str] = None
    s3_prefix: Optional[str] = None


@dataclass
class ModelConfig:
    """Model configuration."""
    type: str = "classification"
    algorithm: str = "random_forest"
    hyperparameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.hyperparameters is None:
            self.hyperparameters = {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            }


@dataclass
class PreprocessingConfig:
    """Preprocessing configuration."""
    numeric_strategy: str = "standard"
    categorical_strategy: str = "onehot"
    handle_outliers: bool = True
    feature_selection_enabled: bool = True
    feature_selection_method: str = "k_best"
    feature_selection_k: int = 10


@dataclass
class MLflowConfig:
    """MLflow configuration."""
    tracking_uri: Optional[str] = None
    experiment_name: str = "default_experiment"
    run_name_prefix: str = "run"
    artifact_location: Optional[str] = None
    registry_uri: Optional[str] = None


@dataclass
class ValidationConfig:
    """Data validation configuration."""
    enabled: bool = True
    create_suite: bool = True
    suite_name: Optional[str] = None
    fail_on_validation_error: bool = False


@dataclass
class InferenceConfig:
    """Inference configuration."""
    batch_size: int = 1000
    confidence_threshold: float = 0.8
    return_probabilities: bool = True
    monitoring_enabled: bool = True


@dataclass
class MLOpsConfig:
    """Complete MLOps configuration."""
    environment: str = "dev"
    aws_region: str = "us-west-2"
    data: DataConfig = None
    model: ModelConfig = None
    preprocessing: PreprocessingConfig = None
    mlflow: MLflowConfig = None
    validation: ValidationConfig = None
    inference: InferenceConfig = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = DataConfig()
        if self.model is None:
            self.model = ModelConfig()
        if self.preprocessing is None:
            self.preprocessing = PreprocessingConfig()
        if self.mlflow is None:
            self.mlflow = MLflowConfig()
        if self.validation is None:
            self.validation = ValidationConfig()
        if self.inference is None:
            self.inference = InferenceConfig()


class ConfigManager:
    """Configuration manager for MLOps platform."""
    
    def __init__(self, 
                 config_dir: str = "config",
                 environment: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
            environment: Environment name (dev, staging, prod)
        """
        self.config_dir = Path(config_dir)
        self.environment = environment or os.getenv("MLOPS_ENV", "dev")
        self.config = None
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
    def load_config(self, config_name: str = "config") -> MLOpsConfig:
        """
        Load configuration from files.
        
        Args:
            config_name: Base name of config file
            
        Returns:
            MLOps configuration
        """
        # Load base config
        base_config = self._load_config_file(f"{config_name}.yaml")
        
        # Load environment-specific config
        env_config_path = self.config_dir / f"{config_name}.{self.environment}.yaml"
        env_config = {}
        if env_config_path.exists():
            env_config = self._load_config_file(f"{config_name}.{self.environment}.yaml")
        
        # Merge configurations (environment overrides base)
        merged_config = self._deep_merge(base_config, env_config)
        
        # Load secrets if available
        secrets = self._load_secrets()
        if secrets:
            merged_config = self._deep_merge(merged_config, secrets)
        
        # Convert to dataclass
        self.config = self._dict_to_config(merged_config)
        
        logger.info(f"Loaded configuration for environment: {self.environment}")
        return self.config
    
    def _load_config_file(self, filename: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = self.config_dir / filename
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            logger.debug(f"Loaded config from: {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return {}
    
    def _load_secrets(self) -> Dict[str, Any]:
        """Load secrets from environment variables or secrets file."""
        secrets = {}
        
        # Load from environment variables
        env_secrets = {
            'mlflow': {
                'tracking_uri': os.getenv('MLFLOW_TRACKING_URI'),
                'registry_uri': os.getenv('MLFLOW_REGISTRY_URI')
            },
            'data': {
                's3_bucket': os.getenv('S3_BUCKET'),
                's3_prefix': os.getenv('S3_PREFIX')
            },
            'aws_region': os.getenv('AWS_REGION')
        }
        
        # Remove None values
        secrets = self._remove_none_values(env_secrets)
        
        # Load from secrets file if exists
        secrets_path = self.config_dir / f"secrets.{self.environment}.yaml"
        if secrets_path.exists():
            try:
                with open(secrets_path, 'r') as f:
                    file_secrets = yaml.safe_load(f) or {}
                secrets = self._deep_merge(secrets, file_secrets)
                logger.debug(f"Loaded secrets from: {secrets_path}")
            except Exception as e:
                logger.error(f"Error loading secrets from {secrets_path}: {e}")
        
        return secrets
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _remove_none_values(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Remove None values from nested dictionary."""
        if not isinstance(d, dict):
            return d
        
        return {
            k: self._remove_none_values(v) 
            for k, v in d.items() 
            if v is not None
        }
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> MLOpsConfig:
        """Convert dictionary to MLOpsConfig dataclass."""
        # Extract nested configurations
        data_config = DataConfig(**config_dict.get('data', {}))
        model_config = ModelConfig(**config_dict.get('model', {}))
        preprocessing_config = PreprocessingConfig(**config_dict.get('preprocessing', {}))
        mlflow_config = MLflowConfig(**config_dict.get('mlflow', {}))
        validation_config = ValidationConfig(**config_dict.get('validation', {}))
        inference_config = InferenceConfig(**config_dict.get('inference', {}))
        
        # Create main config
        main_config = {
            k: v for k, v in config_dict.items() 
            if k not in ['data', 'model', 'preprocessing', 'mlflow', 'validation', 'inference']
        }
        
        return MLOpsConfig(
            data=data_config,
            model=model_config,
            preprocessing=preprocessing_config,
            mlflow=mlflow_config,
            validation=validation_config,
            inference=inference_config,
            **main_config
        )
    
    def save_config(self, config: MLOpsConfig, filename: str = "config.yaml"):
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            filename: Output filename
        """
        config_dict = asdict(config)
        output_path = self.config_dir / filename
        
        with open(output_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
        
        logger.info(f"Saved configuration to: {output_path}")
    
    def create_default_configs(self):
        """Create default configuration files."""
        # Base configuration
        base_config = MLOpsConfig()
        self.save_config(base_config, "config.yaml")
        
        # Environment-specific configurations
        environments = ["dev", "staging", "prod"]
        
        for env in environments:
            env_config = MLOpsConfig(environment=env)
            
            # Environment-specific overrides
            if env == "dev":
                env_config.data.s3_bucket = "mlops-dev-data"
                env_config.mlflow.experiment_name = "dev_experiments"
            elif env == "staging":
                env_config.data.s3_bucket = "mlops-staging-data"
                env_config.mlflow.experiment_name = "staging_experiments"
                env_config.validation.fail_on_validation_error = True
            elif env == "prod":
                env_config.data.s3_bucket = "mlops-prod-data"
                env_config.mlflow.experiment_name = "prod_experiments"
                env_config.validation.fail_on_validation_error = True
                env_config.inference.monitoring_enabled = True
            
            self.save_config(env_config, f"config.{env}.yaml")
        
        # Create example secrets file
        secrets_example = {
            'mlflow': {
                'tracking_uri': 'http://mlflow-server:5000',
                'registry_uri': 'http://mlflow-server:5000'
            },
            'data': {
                's3_bucket': 'your-s3-bucket',
                's3_prefix': 'data/'
            }
        }
        
        secrets_path = self.config_dir / "secrets.example.yaml"
        with open(secrets_path, 'w') as f:
            yaml.dump(secrets_example, f, default_flow_style=False, indent=2)
        
        logger.info("Created default configuration files")
    
    def validate_config(self, config: MLOpsConfig) -> bool:
        """
        Validate configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid, False otherwise
        """
        errors = []
        
        # Validate model type
        if config.model.type not in ["classification", "regression"]:
            errors.append(f"Invalid model type: {config.model.type}")
        
        # Validate algorithms
        valid_algorithms = ["random_forest", "xgboost", "linear_regression", "logistic_regression"]
        if config.model.algorithm not in valid_algorithms:
            errors.append(f"Invalid algorithm: {config.model.algorithm}")
        
        # Validate data format
        if config.data.format not in ["csv", "parquet", "json"]:
            errors.append(f"Invalid data format: {config.data.format}")
        
        # Validate test/validation sizes
        if not 0 < config.data.test_size < 1:
            errors.append(f"Invalid test_size: {config.data.test_size}")
        
        if not 0 < config.data.validation_size < 1:
            errors.append(f"Invalid validation_size: {config.data.validation_size}")
        
        # Validate preprocessing strategies
        if config.preprocessing.numeric_strategy not in ["standard", "minmax", "robust"]:
            errors.append(f"Invalid numeric_strategy: {config.preprocessing.numeric_strategy}")
        
        if config.preprocessing.categorical_strategy not in ["onehot", "ordinal", "label"]:
            errors.append(f"Invalid categorical_strategy: {config.preprocessing.categorical_strategy}")
        
        if errors:
            for error in errors:
                logger.error(f"Config validation error: {error}")
            return False
        
        logger.info("Configuration validation passed")
        return True
    
    def get_config_summary(self, config: MLOpsConfig) -> str:
        """
        Get a summary of the configuration.
        
        Args:
            config: Configuration to summarize
            
        Returns:
            Configuration summary string
        """
        summary = f"""
MLOps Configuration Summary
===========================
Environment: {config.environment}
AWS Region: {config.aws_region}

Data Configuration:
- Source: {config.data.source}
- Format: {config.data.format}
- Target Column: {config.data.target_column}
- Test Size: {config.data.test_size}
- Validation Size: {config.data.validation_size}

Model Configuration:
- Type: {config.model.type}
- Algorithm: {config.model.algorithm}
- Hyperparameters: {config.model.hyperparameters}

Preprocessing:
- Numeric Strategy: {config.preprocessing.numeric_strategy}
- Categorical Strategy: {config.preprocessing.categorical_strategy}
- Feature Selection: {config.preprocessing.feature_selection_enabled}

MLflow:
- Experiment Name: {config.mlflow.experiment_name}
- Tracking URI: {config.mlflow.tracking_uri or 'Default'}

Validation:
- Enabled: {config.validation.enabled}
- Fail on Error: {config.validation.fail_on_validation_error}

Inference:
- Batch Size: {config.inference.batch_size}
- Confidence Threshold: {config.inference.confidence_threshold}
- Monitoring: {config.inference.monitoring_enabled}
"""
        return summary.strip()


# Example usage
def config_example():
    """Example of using the configuration manager."""
    # Initialize config manager
    config_manager = ConfigManager(environment="dev")
    
    # Create default configs
    config_manager.create_default_configs()
    
    # Load configuration
    config = config_manager.load_config()
    
    # Validate configuration
    is_valid = config_manager.validate_config(config)
    print(f"Configuration valid: {is_valid}")
    
    # Print summary
    print(config_manager.get_config_summary(config))
    
    return config_manager, config


if __name__ == "__main__":
    config_manager, config = config_example()