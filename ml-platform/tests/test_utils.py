"""
Tests for Utils modules (ConfigManager, LoggingConfig).

These tests verify configuration management and logging setup
without requiring external services.
"""

import logging
import os
import tempfile

import pytest
import yaml

from src.utils.config_manager import (
    ConfigManager,
    DataConfig,
    InferenceConfig,
    MLflowConfig,
    MLOpsConfig,
    ModelConfig,
    PreprocessingConfig,
    ValidationConfig,
)
from src.utils.logging_config import (
    MLOpsLogger,
    create_logging_config_file,
    get_default_logging_config,
    setup_logging,
)


class TestConfigManager:
    """Tests for configuration management."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def base_config_dict(self):
        """Return a basic configuration dictionary."""
        return {
            "environment": "dev",
            "aws_region": "us-west-2",
            "data": {
                "source": "local",
                "format": "csv",
                "target_column": "target",
                "test_size": 0.2,
                "validation_size": 0.1,
            },
            "model": {
                "type": "classification",
                "algorithm": "random_forest",
                "hyperparameters": {"n_estimators": 50},
            },
            "preprocessing": {
                "numeric_strategy": "standard",
                "categorical_strategy": "onehot",
                "feature_selection_enabled": True,
            },
            "mlflow": {"experiment_name": "test_experiment"},
            "validation": {"enabled": True, "fail_on_validation_error": False},
            "inference": {"batch_size": 500, "confidence_threshold": 0.7},
        }

    def test_initialization(self, temp_config_dir):
        """Test config manager initialization."""
        manager = ConfigManager(config_dir=temp_config_dir, environment="staging")
        assert manager.environment == "staging"
        assert os.path.exists(temp_config_dir)

    def test_default_initialization(self, temp_config_dir, monkeypatch):
        """Test default environment from env var."""
        monkeypatch.setenv("MLOPS_ENV", "prod")
        manager = ConfigManager(config_dir=temp_config_dir)
        assert manager.environment == "prod"

    def test_load_config(self, temp_config_dir, base_config_dict):
        """Test loading configuration from file."""
        config_path = os.path.join(temp_config_dir, "config.yaml")
        with open(config_path, "w") as f:
            yaml.dump(base_config_dict, f)

        manager = ConfigManager(config_dir=temp_config_dir)
        config = manager.load_config("config")

        assert isinstance(config, MLOpsConfig)
        assert config.environment == "dev"
        assert config.aws_region == "us-west-2"
        assert config.data.source == "local"
        assert config.model.type == "classification"
        assert config.mlflow.experiment_name == "test_experiment"

    def test_load_config_with_env_override(self, temp_config_dir, base_config_dict):
        """Test environment-specific config overrides base."""
        base_config_dict["environment"] = "dev"
        config_path = os.path.join(temp_config_dir, "config.yaml")
        with open(config_path, "w") as f:
            yaml.dump(base_config_dict, f)

        env_config = {"model": {"type": "regression"}, "environment": "staging"}
        env_path = os.path.join(temp_config_dir, "config.staging.yaml")
        with open(env_path, "w") as f:
            yaml.dump(env_config, f)

        manager = ConfigManager(config_dir=temp_config_dir, environment="staging")
        config = manager.load_config("config")

        assert config.environment == "staging"
        assert config.model.type == "regression"
        assert config.data.source == "local"  # From base

    def test_load_secrets_from_env(self, temp_config_dir, base_config_dict, monkeypatch):
        """Test loading secrets from environment variables."""
        monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow-test:5000")
        monkeypatch.setenv("AWS_REGION", "eu-west-1")

        config_path = os.path.join(temp_config_dir, "config.yaml")
        with open(config_path, "w") as f:
            yaml.dump(base_config_dict, f)

        manager = ConfigManager(config_dir=temp_config_dir)
        config = manager.load_config("config")

        assert config.mlflow.tracking_uri == "http://mlflow-test:5000"
        assert config.aws_region == "eu-west-1"

    def test_save_config(self, temp_config_dir):
        """Test saving configuration to file."""
        manager = ConfigManager(config_dir=temp_config_dir)
        config = MLOpsConfig(environment="test", aws_region="us-east-1")
        manager.save_config(config, "saved_config.yaml")

        saved_path = os.path.join(temp_config_dir, "saved_config.yaml")
        assert os.path.exists(saved_path)

        with open(saved_path, "r") as f:
            loaded = yaml.safe_load(f)
        assert loaded["environment"] == "test"
        assert loaded["aws_region"] == "us-east-1"

    def test_validate_config_valid(self, temp_config_dir, base_config_dict):
        """Test validation of a valid configuration."""
        config_path = os.path.join(temp_config_dir, "config.yaml")
        with open(config_path, "w") as f:
            yaml.dump(base_config_dict, f)

        manager = ConfigManager(config_dir=temp_config_dir)
        config = manager.load_config("config")
        assert manager.validate_config(config) is True

    def test_validate_config_invalid(self, temp_config_dir):
        """Test validation catches invalid configuration."""
        invalid_config = {
            "environment": "dev",
            "model": {"type": "unsupported_type", "algorithm": "random_forest"},
            "data": {"format": "csv", "test_size": 1.5, "validation_size": 0.1},
            "preprocessing": {
                "numeric_strategy": "invalid",
                "categorical_strategy": "onehot",
            },
        }
        config_path = os.path.join(temp_config_dir, "config.yaml")
        with open(config_path, "w") as f:
            yaml.dump(invalid_config, f)

        manager = ConfigManager(config_dir=temp_config_dir)
        config = manager.load_config("config")
        assert manager.validate_config(config) is False

    def test_create_default_configs(self, temp_config_dir):
        """Test creation of default configuration files."""
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.create_default_configs()

        assert os.path.exists(os.path.join(temp_config_dir, "config.yaml"))
        assert os.path.exists(os.path.join(temp_config_dir, "config.dev.yaml"))
        assert os.path.exists(os.path.join(temp_config_dir, "config.staging.yaml"))
        assert os.path.exists(os.path.join(temp_config_dir, "config.prod.yaml"))
        assert os.path.exists(os.path.join(temp_config_dir, "secrets.example.yaml"))

    def test_get_config_summary(self, temp_config_dir, base_config_dict):
        """Test configuration summary generation."""
        config_path = os.path.join(temp_config_dir, "config.yaml")
        with open(config_path, "w") as f:
            yaml.dump(base_config_dict, f)

        manager = ConfigManager(config_dir=temp_config_dir)
        config = manager.load_config("config")
        summary = manager.get_config_summary(config)

        assert "MLOps Configuration Summary" in summary
        assert "Environment: dev" in summary
        assert "classification" in summary
        assert "random_forest" in summary

    def test_deep_merge(self):
        """Test deep merge utility."""
        manager = ConfigManager(config_dir=".")
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"c": 99}, "e": 5}
        merged = manager._deep_merge(base, override)
        assert merged["a"] == 1
        assert merged["b"]["c"] == 99
        assert merged["b"]["d"] == 3
        assert merged["e"] == 5


class TestDataclasses:
    """Tests for configuration dataclasses."""

    def test_data_config_defaults(self):
        """Test DataConfig default values."""
        config = DataConfig()
        assert config.source == "local"
        assert config.format == "csv"
        assert config.target_column == "target"

    def test_model_config_post_init(self):
        """Test ModelConfig post-init hyperparameters."""
        config = ModelConfig()
        assert config.hyperparameters is not None
        assert "n_estimators" in config.hyperparameters

    def test_mlops_config_post_init(self):
        """Test MLOpsConfig initializes nested configs."""
        config = MLOpsConfig()
        assert config.data is not None
        assert config.model is not None
        assert config.preprocessing is not None
        assert config.mlflow is not None
        assert config.validation is not None
        assert config.inference is not None


class TestLoggingConfig:
    """Tests for logging configuration utilities."""

    def test_get_default_logging_config(self):
        """Test default logging config structure."""
        config = get_default_logging_config()
        assert config["version"] == 1
        assert "formatters" in config
        assert "handlers" in config
        assert "loggers" in config
        assert "standard" in config["formatters"]
        assert "console" in config["handlers"]

    def test_setup_logging_default(self):
        """Test setup logging with default fallback."""
        setup_logging(config_path="/nonexistent/path.yaml")
        logger = logging.getLogger("test_logger")
        assert logger is not None

    def test_create_logging_config_file(self):
        """Test creating logging config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "logging.yaml")
            create_logging_config_file(output_path)
            assert os.path.exists(output_path)

            with open(output_path, "r") as f:
                config = yaml.safe_load(f)
            assert config["version"] == 1

    def test_mlops_logger(self, caplog):
        """Test MLOpsLogger structured logging."""
        setup_logging()
        logger = MLOpsLogger("test")

        with caplog.at_level(logging.INFO, logger="mlops_platform.test"):
            logger.log_data_operation("load", {"rows": 100})
            assert "DATA_OP: load" in caplog.text

    def test_mlops_logger_model_operation(self, caplog):
        """Test model operation logging."""
        setup_logging()
        logger = MLOpsLogger("test")

        with caplog.at_level(logging.INFO, logger="mlops_platform.test"):
            logger.log_model_operation("train", "rf", {"accuracy": 0.9})
            assert "MODEL_OP: train" in caplog.text

    def test_mlops_logger_pipeline_step(self, caplog):
        """Test pipeline step logging."""
        setup_logging()
        logger = MLOpsLogger("test")

        with caplog.at_level(logging.INFO, logger="mlops_platform.test"):
            logger.log_pipeline_step("preprocess", "completed", 1.5)
            assert "PIPELINE_STEP: preprocess" in caplog.text

    def test_mlops_logger_metric(self, caplog):
        """Test metric logging."""
        setup_logging()
        logger = MLOpsLogger("test")

        with caplog.at_level(logging.INFO, logger="mlops_platform.test"):
            logger.log_metric("accuracy", 0.95)
            assert "METRIC: accuracy = 0.95" in caplog.text

    def test_mlops_logger_error(self, caplog):
        """Test error logging."""
        setup_logging()
        logger = MLOpsLogger("test")

        with caplog.at_level(logging.ERROR, logger="mlops_platform.test"):
            try:
                raise ValueError("Test error")
            except Exception as e:
                logger.log_error(e, {"component": "test"})
            assert "ERROR: ValueError" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__])
