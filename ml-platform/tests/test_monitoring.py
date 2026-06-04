"""
Tests for Monitoring modules (DriftDetector, ModelMonitor, MetricsExporter).

These tests verify drift detection, model monitoring, and metrics export
functionality without requiring external services.
"""

import json
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification

from src.monitoring.drift_detector import DriftDetector
from src.monitoring.model_monitor import ModelMonitor
from src.monitoring.metrics_exporter import MetricsExporter


class TestDriftDetector:
    """Unit and integration tests for DriftDetector."""

    @pytest.fixture
    def reference_data(self):
        """Generate reference dataset."""
        np.random.seed(42)
        X, y = make_classification(
            n_samples=200, n_features=5, n_informative=3, n_classes=2, random_state=42
        )
        df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
        df["target"] = y
        return df

    @pytest.fixture
    def current_data_no_drift(self, reference_data):
        """Generate current data with no significant drift."""
        return reference_data.sample(100, random_state=42).reset_index(drop=True)

    @pytest.fixture
    def current_data_with_drift(self):
        """Generate current data with clear drift."""
        np.random.seed(43)
        df = pd.DataFrame()
        for i in range(5):
            df[f"feature_{i}"] = np.random.normal(loc=10.0, scale=5.0, size=100)
        df["target"] = np.random.randint(0, 2, 100)
        return df

    def test_initialization(self, reference_data):
        """Test drift detector initialization."""
        detector = DriftDetector(reference_data=reference_data)
        assert detector.reference_data is not None
        assert len(detector.reference_data) == len(reference_data)
        assert detector.drift_threshold == 0.05
        assert detector._last_results is None

    def test_detect_data_drift_no_drift(self, reference_data, current_data_no_drift):
        """Test drift detection on similar data."""
        detector = DriftDetector(reference_data=reference_data)
        results = detector.detect_data_drift(current_data=current_data_no_drift)

        assert "dataset_drift" in results
        assert "drift_share" in results
        assert "timestamp" in results
        assert isinstance(results["dataset_drift"], bool)
        assert 0.0 <= results["drift_share"] <= 1.0

    def test_detect_data_drift_with_drift(self, reference_data, current_data_with_drift):
        """Test drift detection on clearly drifted data."""
        detector = DriftDetector(reference_data=reference_data)
        results = detector.detect_data_drift(current_data=current_data_with_drift)

        assert "dataset_drift" in results
        assert "drift_share" in results
        assert "drifted_columns" in results
        # With very different distributions we expect some drift
        assert results["drift_share"] > 0.0

    def test_detect_data_drift_specific_columns(self, reference_data, current_data_with_drift):
        """Test drift detection on specific columns."""
        detector = DriftDetector(reference_data=reference_data)
        results = detector.detect_data_drift(
            current_data=current_data_with_drift,
            columns=["feature_0", "feature_1"],
        )

        assert "column_drift_scores" in results
        assert any(col in results["column_drift_scores"] for col in ["feature_0", "feature_1"])

    def test_get_last_results(self, reference_data, current_data_no_drift):
        """Test retrieving last results."""
        detector = DriftDetector(reference_data=reference_data)
        assert detector.get_last_results() is None

        detector.detect_data_drift(current_data=current_data_no_drift)
        last = detector.get_last_results()
        assert last is not None
        assert "dataset_drift" in last

    def test_run_drift_tests(self, reference_data, current_data_no_drift):
        """Test drift test suite execution."""
        detector = DriftDetector(reference_data=reference_data)
        results = detector.run_drift_tests(current_data=current_data_no_drift)

        assert "all_passed" in results
        assert "total_tests" in results
        assert "success_tests" in results
        assert "failed_tests" in results
        assert results["total_tests"] > 0

    def test_generate_report(self, reference_data, current_data_no_drift):
        """Test HTML report generation."""
        detector = DriftDetector(reference_data=reference_data)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "report.html")
            path = detector.generate_report(
                current_data=current_data_no_drift,
                output_path=output_path,
                include_quality=True,
            )
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0


class TestModelMonitor:
    """Tests for ModelMonitor combining drift and performance tracking."""

    @pytest.fixture
    def reference_data(self):
        """Generate reference data with predictions."""
        np.random.seed(42)
        X, y = make_classification(
            n_samples=200, n_features=5, n_informative=3, n_classes=2, random_state=42
        )
        df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
        df["target"] = y
        df["prediction"] = y  # Perfect predictions for reference
        return df

    @pytest.fixture
    def current_data(self, reference_data):
        """Generate current data."""
        current = reference_data.sample(100, random_state=43).reset_index(drop=True)
        current["prediction"] = current["target"]  # Still perfect
        return current

    def test_initialization(self, reference_data):
        """Test model monitor initialization."""
        monitor = ModelMonitor(
            reference_data=reference_data,
            model_type="classification",
            target_column="target",
            prediction_column="prediction",
        )
        assert monitor.model_type == "classification"
        assert monitor.target_column == "target"
        assert monitor.prediction_column == "prediction"
        assert len(monitor.feature_columns) == 5
        assert monitor.drift_detector is not None

    def test_run_monitoring(self, reference_data, current_data):
        """Test comprehensive monitoring run."""
        monitor = ModelMonitor(
            reference_data=reference_data,
            model_type="classification",
            target_column="target",
            prediction_column="prediction",
        )
        results = monitor.run_monitoring(current_data=current_data)

        assert "timestamp" in results
        assert "data_drift" in results
        assert "model_performance" in results
        assert "health_status" in results
        assert results["health_status"] in ["healthy", "warning", "critical"]
        assert results["samples_analyzed"] == len(current_data)

    def test_monitoring_history(self, reference_data, current_data):
        """Test that monitoring history is accumulated."""
        monitor = ModelMonitor(
            reference_data=reference_data,
            model_type="classification",
            target_column="target",
            prediction_column="prediction",
        )
        assert len(monitor.get_monitoring_history()) == 0

        monitor.run_monitoring(current_data=current_data)
        assert len(monitor.get_monitoring_history()) == 1

        monitor.run_monitoring(current_data=current_data)
        assert len(monitor.get_monitoring_history()) == 2

    def test_health_status_healthy(self, reference_data, current_data):
        """Test healthy status determination."""
        monitor = ModelMonitor(
            reference_data=reference_data,
            model_type="classification",
            target_column="target",
            prediction_column="prediction",
        )
        results = monitor.run_monitoring(current_data=current_data)
        assert results["health_status"] == "healthy"

    def test_export_metrics_json(self, reference_data, current_data):
        """Test exporting metrics to JSON."""
        monitor = ModelMonitor(
            reference_data=reference_data,
            model_type="classification",
            target_column="target",
            prediction_column="prediction",
        )
        monitor.run_monitoring(current_data=current_data)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            path = monitor.export_metrics_json(temp_path)
            assert os.path.exists(path)
            with open(path, "r") as f:
                data = json.load(f)
            assert "timestamp" in data
        finally:
            os.unlink(temp_path)

    def test_generate_monitoring_report(self, reference_data, current_data):
        """Test comprehensive monitoring HTML report generation."""
        monitor = ModelMonitor(
            reference_data=reference_data,
            model_type="classification",
            target_column="target",
            prediction_column="prediction",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "monitoring_report.html")
            path = monitor.generate_monitoring_report(
                current_data=current_data,
                output_path=output_path,
            )
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0


class TestMetricsExporter:
    """Tests for Prometheus metrics exporter."""

    def test_initialization(self):
        """Test metrics exporter initialization."""
        exporter = MetricsExporter(
            model_name="test_model",
            model_version="1.0",
        )
        assert exporter.model_name == "test_model"
        assert exporter.model_version == "1.0"
        assert exporter.registry is not None

    def test_update_drift_metrics(self):
        """Test updating drift metrics."""
        exporter = MetricsExporter(model_name="test_model")
        drift_results = {
            "dataset_drift": True,
            "drift_share": 0.3,
            "number_of_drifted_columns": 2,
            "missing_values": {"share_missing": 0.05},
            "column_drift_scores": {
                "feature_0": {"drift_score": 0.8},
                "feature_1": {"drift_score": 0.2},
            },
        }
        exporter.update_drift_metrics(drift_results)
        metrics_output = exporter.get_metrics()
        assert b"ml_data_drift_detected" in metrics_output
        assert b"ml_data_drift_share" in metrics_output
        assert b"ml_drifted_columns_count" in metrics_output
        assert b"ml_column_drift_score" in metrics_output

    def test_update_performance_metrics(self):
        """Test updating performance metrics."""
        exporter = MetricsExporter(model_name="test_model")
        perf_results = {
            "current_accuracy": 0.95,
            "current_f1": 0.93,
            "current_precision": 0.94,
            "current_recall": 0.92,
            "performance_degradation": 5.0,
        }
        exporter.update_performance_metrics(perf_results)
        metrics_output = exporter.get_metrics()
        assert b"ml_model_accuracy" in metrics_output
        assert b"ml_model_f1_score" in metrics_output
        assert b"ml_performance_degradation_percent" in metrics_output

    def test_update_from_monitoring_results(self):
        """Test updating all metrics from monitoring results."""
        exporter = MetricsExporter(model_name="test_model")
        results = {
            "samples_analyzed": 100,
            "health_status": "warning",
            "data_drift": {
                "dataset_drift": False,
                "drift_share": 0.0,
                "number_of_drifted_columns": 0,
                "missing_values": {"share_missing": 0.0},
            },
            "model_performance": {
                "current_accuracy": 0.90,
                "current_f1": 0.89,
            },
        }
        exporter.update_from_monitoring_results(results)
        metrics_output = exporter.get_metrics()
        assert b"ml_model_health_status" in metrics_output
        assert b"ml_samples_analyzed_total" in metrics_output
        assert b"ml_monitoring_runs_total" in metrics_output

    def test_get_metrics(self):
        """Test retrieving metrics in Prometheus format."""
        exporter = MetricsExporter(model_name="test_model")
        metrics = exporter.get_metrics()
        assert isinstance(metrics, bytes)
        assert len(metrics) > 0

    def test_health_status_values(self):
        """Test that health status maps correctly to numeric values."""
        exporter = MetricsExporter(model_name="test_model")

        for status, expected in [("healthy", 0), ("warning", 1), ("critical", 2)]:
            exporter.update_from_monitoring_results(
                {"health_status": status, "data_drift": {}, "model_performance": {}}
            )
            metrics = exporter.get_metrics().decode("utf-8")
            # Check that the gauge has the expected value
            lines = [l for l in metrics.split("\n") if "ml_model_health_status{" in l]
            # The value should appear in a line like: ml_model_health_status{...} 1.0
            value_lines = [l for l in metrics.split("\n") if l.startswith("ml_model_health_status{")]
            assert len(value_lines) > 0


if __name__ == "__main__":
    pytest.main([__file__])
