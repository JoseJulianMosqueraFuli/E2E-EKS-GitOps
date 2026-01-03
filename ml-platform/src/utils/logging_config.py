"""
Logging Configuration

Centralized logging configuration for the MLOps platform.
"""

import logging
import logging.config
import os
from typing import Optional, Dict, Any
import yaml


def setup_logging(
    config_path: Optional[str] = None,
    default_level: int = logging.INFO,
    env_key: str = 'LOG_CFG'
) -> None:
    """
    Setup logging configuration.
    
    Args:
        config_path: Path to logging configuration file
        default_level: Default logging level
        env_key: Environment variable for config path
    """
    # Check environment variable first
    path = config_path or os.getenv(env_key, None)
    
    if path and os.path.exists(path):
        with open(path, 'rt') as f:
            try:
                config = yaml.safe_load(f.read())
                logging.config.dictConfig(config)
                print(f"Loaded logging config from {path}")
                return
            except Exception as e:
                print(f"Error loading logging config: {e}")
    
    # Fallback to default configuration
    logging.basicConfig(
        level=default_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific loggers
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('mlflow').setLevel(logging.INFO)


def get_default_logging_config() -> Dict[str, Any]:
    """
    Get default logging configuration dictionary.
    
    Returns:
        Logging configuration dictionary
    """
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'json': {
                'format': '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "module": "%(module)s", "function": "%(funcName)s", "message": "%(message)s"}',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'detailed',
                'filename': 'logs/mlops_platform.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'detailed',
                'filename': 'logs/errors.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False
            },
            'mlops_platform': {
                'handlers': ['console', 'file', 'error_file'],
                'level': 'DEBUG',
                'propagate': False
            },
            'boto3': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False
            },
            'botocore': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False
            },
            'urllib3': {
                'handlers': ['file'],
                'level': 'WARNING',
                'propagate': False
            },
            'mlflow': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False
            }
        }
    }


def create_logging_config_file(output_path: str = "config/logging.yaml") -> None:
    """
    Create a logging configuration file with default settings.
    
    Args:
        output_path: Path where to save the config file
    """
    config = get_default_logging_config()
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"Created logging config file: {output_path}")


class MLOpsLogger:
    """Custom logger class for MLOps operations."""
    
    def __init__(self, name: str):
        """
        Initialize MLOps logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(f"mlops_platform.{name}")
    
    def log_data_operation(self, operation: str, details: Dict[str, Any]):
        """Log data operation with structured information."""
        self.logger.info(f"DATA_OP: {operation}", extra=details)
    
    def log_model_operation(self, operation: str, model_name: str, details: Dict[str, Any]):
        """Log model operation with structured information."""
        self.logger.info(f"MODEL_OP: {operation} - {model_name}", extra=details)
    
    def log_pipeline_step(self, step: str, status: str, duration: float, details: Dict[str, Any] = None):
        """Log pipeline step with timing information."""
        extra = {
            'step': step,
            'status': status,
            'duration': duration
        }
        if details:
            extra.update(details)
        
        self.logger.info(f"PIPELINE_STEP: {step} - {status} ({duration:.2f}s)", extra=extra)
    
    def log_metric(self, metric_name: str, value: float, context: Dict[str, Any] = None):
        """Log metric with context."""
        extra = {
            'metric_name': metric_name,
            'metric_value': value
        }
        if context:
            extra.update(context)
        
        self.logger.info(f"METRIC: {metric_name} = {value}", extra=extra)
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with context."""
        extra = {
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        if context:
            extra.update(context)
        
        self.logger.error(f"ERROR: {type(error).__name__}: {error}", extra=extra, exc_info=True)


# Example usage
if __name__ == "__main__":
    # Create default logging config
    create_logging_config_file()
    
    # Setup logging
    setup_logging("config/logging.yaml")
    
    # Test logging
    logger = MLOpsLogger("test")
    
    logger.log_data_operation("load_data", {
        "source": "s3://bucket/data.csv",
        "rows": 1000,
        "columns": 10
    })
    
    logger.log_model_operation("train", "random_forest_classifier", {
        "algorithm": "random_forest",
        "n_estimators": 100,
        "accuracy": 0.95
    })
    
    logger.log_pipeline_step("feature_engineering", "completed", 2.5, {
        "input_features": 20,
        "output_features": 15
    })
    
    logger.log_metric("accuracy", 0.95, {"model": "rf_classifier", "dataset": "test"})
    
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.log_error(e, {"component": "test", "operation": "example"})