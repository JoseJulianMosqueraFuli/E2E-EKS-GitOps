"""
Tests for DataValidator using Great Expectations.

These tests verify data quality validation functionality
without requiring external services.
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from src.data.data_validator import DataValidator


class TestDataValidator:
    """Tests for DataValidator."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for validation."""
        np.random.seed(42)
        return pd.DataFrame({
            "id": range(100),
            "feature_1": np.random.normal(0, 1, 100),
            "feature_2": np.random.uniform(0, 100, 100),
            "category": np.random.choice(["A", "B", "C"], 100),
            "target": np.random.randint(0, 2, 100),
        })

    @pytest.fixture
    def validator(self):
        """Create a DataValidator instance."""
        return DataValidator(context_root_dir="./gx_test")

    def test_initialization(self):
        """Test validator initialization."""
        validator = DataValidator()
        assert validator.context_root_dir == "./gx"
        assert validator._context is None
        assert validator.context is not None

    def test_create_expectation_suite(self, validator, sample_data):
        """Test creating an expectation suite from data."""
        suite_name = "test_suite"
        result = validator.create_expectation_suite(
            suite_name, sample_data, overwrite=True
        )
        assert result == suite_name

        # Verify suite exists
        suite = validator.context.suites.get(suite_name)
        assert suite is not None

    def test_validate_data_pass(self, validator, sample_data):
        """Test data validation that should pass."""
        suite_name = "test_validate_pass"
        validator.create_expectation_suite(suite_name, sample_data.head(50), overwrite=True)

        results = validator.validate_data(sample_data, suite_name)
        assert "success" in results
        assert "run_name" in results
        assert "suite_name" in results
        assert results["suite_name"] == suite_name
        assert results["evaluated_expectations"] > 0
        assert results["success_percent"] >= 0.0

    def test_validate_data_with_run_name(self, validator, sample_data):
        """Test validation with custom run name."""
        suite_name = "test_run_name"
        validator.create_expectation_suite(suite_name, sample_data.head(50), overwrite=True)

        results = validator.validate_data(sample_data, suite_name, run_name="custom_run")
        assert results["run_name"] == "custom_run"

    def test_create_data_quality_suite(self, validator):
        """Test creating a predefined data quality suite."""
        suite_name = validator.create_data_quality_suite("data_quality_test")
        assert suite_name == "data_quality_test"

        suite = validator.context.suites.get(suite_name)
        assert suite is not None

    def test_get_validation_report_url(self, validator):
        """Test getting validation report URL."""
        url = validator.get_validation_report_url()
        assert isinstance(url, str)

    def test_suite_overwrite(self, validator, sample_data):
        """Test overwriting an existing suite."""
        suite_name = "overwrite_test"
        validator.create_expectation_suite(suite_name, sample_data, overwrite=False)

        # Modify data and overwrite
        modified_data = sample_data.copy()
        modified_data["new_column"] = range(len(modified_data))
        validator.create_expectation_suite(suite_name, modified_data, overwrite=True)

        suite = validator.context.suites.get(suite_name)
        assert suite is not None

    def test_validate_data_with_missing_values(self, validator):
        """Test validation with data containing missing values."""
        np.random.seed(42)
        data = pd.DataFrame({
            "feature_1": np.random.normal(0, 1, 100),
            "feature_2": np.random.uniform(0, 100, 100),
        })
        # Introduce some missing values
        data.loc[data.sample(10).index, "feature_1"] = np.nan

        suite_name = "missing_values_test"
        validator.create_expectation_suite(suite_name, data.head(50), overwrite=True)

        results = validator.validate_data(data, suite_name)
        assert "success" in results
        assert results["evaluated_expectations"] > 0

    def test_validate_data_with_categorical(self, validator):
        """Test validation with categorical columns."""
        data = pd.DataFrame({
            "category": np.random.choice(["A", "B", "C", "D"], 200),
            "label": np.random.choice(["X", "Y"], 200),
        })

        suite_name = "categorical_test"
        validator.create_expectation_suite(suite_name, data.head(50), overwrite=True)

        results = validator.validate_data(data, suite_name)
        assert "success" in results
        assert results["evaluated_expectations"] > 0

    def test_multiple_validations(self, validator, sample_data):
        """Test running multiple validations sequentially."""
        suite_name = "multi_validation"
        validator.create_expectation_suite(suite_name, sample_data.head(50), overwrite=True)

        results1 = validator.validate_data(sample_data, suite_name, run_name="run_1")
        results2 = validator.validate_data(sample_data, suite_name, run_name="run_2")

        assert results1["run_name"] == "run_1"
        assert results2["run_name"] == "run_2"
        assert results1["success"] == results2["success"]

    def test_empty_data(self, validator):
        """Test handling of edge cases with small data."""
        data = pd.DataFrame({"feature": [1, 2, 3], "target": [0, 1, 0]})

        suite_name = "small_data_test"
        validator.create_expectation_suite(suite_name, data, overwrite=True)

        results = validator.validate_data(data, suite_name)
        assert "success" in results
        assert results["evaluated_expectations"] > 0


if __name__ == "__main__":
    pytest.main([__file__])
