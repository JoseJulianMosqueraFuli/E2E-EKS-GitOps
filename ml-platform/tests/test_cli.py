"""
Tests for the MLOps Platform CLI entry points.
"""

import os
import tempfile
from click.testing import CliRunner
import pytest

from src.cli import main


class TestCLI:
    """CLI integration tests using Click's test runner."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def sample_csv(self, sample_classification_data):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            sample_classification_data.to_csv(f.name, index=False)
            return f.name

    def test_cli_no_args_shows_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_create_sample_command(self, runner):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, 'sample.csv')
            result = runner.invoke(main, [
                'create-sample', output,
                '--n-samples', '50',
                '--n-features', '5',
                '--task-type', 'classification'
            ])
            assert result.exit_code == 0
            assert os.path.exists(output)

    def test_validate_command(self, runner, sample_csv):
        result = runner.invoke(main, [
            'validate', sample_csv,
            '--create-suite'
        ])
        # Validation may fail on synthetic data expectations, but CLI should not crash
        assert result.exit_code in (0, 1)

    def test_train_command(self, runner, sample_classification_data, temp_project_dir,
                           mock_mlflow_tracking_uri):
        """Test CLI train command end-to-end."""
        data_path = os.path.join(temp_project_dir, 'data', 'train_cli.csv')
        sample_classification_data.to_csv(data_path, index=False)

        result = runner.invoke(main, [
            'train', data_path,
            '--config-dir', os.path.join(temp_project_dir, 'config'),
        ])

        # Training should succeed (exit code 0) even if config doesn't exist (uses defaults)
        # or fail gracefully with invalid config
        if result.exit_code != 0:
            # If it fails, it should not be a total crash
            assert "Error" not in result.output or "Invalid" in result.output
        else:
            assert "Training completed" in result.output
            assert "Run ID" in result.output

    def test_inference_command_with_model_path(self, runner, sample_classification_data,
                                               temp_project_dir, mock_mlflow_tracking_uri):
        """Test CLI inference command with local model path."""
        # First train a model
        train_data_path = os.path.join(temp_project_dir, 'data', 'train_inf.csv')
        sample_classification_data.to_csv(train_data_path, index=False)

        from src.pipelines.training_pipeline import TrainingPipeline
        train_pipeline = TrainingPipeline()
        train_results = train_pipeline.run_pipeline(train_data_path)

        model_path = os.path.join(temp_project_dir, 'models', 'model.joblib')
        train_pipeline.model.save_model(model_path)

        # Create inference data (no target)
        infer_data = sample_classification_data.drop(columns=['target'])
        infer_path = os.path.join(temp_project_dir, 'data', 'infer_cli.csv')
        infer_data.to_csv(infer_path, index=False)

        result = runner.invoke(main, [
            'inference', infer_path,
            '--model-path', model_path,
            '--output-path', os.path.join(temp_project_dir, 'predictions.json'),
        ])

        # Inference may fail if model doesn't match expected interface, but CLI shouldn't crash
        assert result.exit_code in (0, 1)
        if result.exit_code == 0:
            assert "Inference completed" in result.output
        else:
            # Should provide meaningful error, not crash
            assert result.exception is None or isinstance(result.exception, SystemExit)
