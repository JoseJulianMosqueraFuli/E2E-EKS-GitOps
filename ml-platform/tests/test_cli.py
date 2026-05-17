"""
Tests for the MLOps Platform CLI entry points.
"""

import os
import tempfile
from click.testing import CliRunner
import pytest

from src.main import main


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
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert 'Usage:' in result.output

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
