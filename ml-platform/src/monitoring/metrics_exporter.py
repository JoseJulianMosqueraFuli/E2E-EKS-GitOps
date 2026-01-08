"""
Metrics Exporter Module

Exports drift and monitoring metrics to Prometheus.
"""

import logging
from typing import Any, Dict, Optional

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    push_to_gateway,
    start_http_server,
)

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Exports model monitoring metrics to Prometheus."""

    def __init__(
        self,
        model_name: str,
        model_version: str = "1.0",
        registry: Optional[CollectorRegistry] = None,
    ):
        """
        Initialize metrics exporter.

        Args:
            model_name: Name of the model being monitored
            model_version: Version of the model
            registry: Prometheus registry (creates new if None)
        """
        self.model_name = model_name
        self.model_version = model_version
        self.registry = registry or CollectorRegistry()

        self._setup_metrics()

    def _setup_metrics(self):
        """Setup Prometheus metrics."""
        labels = ["model_name", "model_version"]

        # Drift metrics
        self.drift_detected = Gauge(
            "ml_data_drift_detected",
            "Whether data drift was detected (1=yes, 0=no)",
            labels,
            registry=self.registry,
        )

        self.drift_share = Gauge(
            "ml_data_drift_share",
            "Share of features with detected drift",
            labels,
            registry=self.registry,
        )

        self.drifted_columns_count = Gauge(
            "ml_drifted_columns_count",
            "Number of columns with detected drift",
            labels,
            registry=self.registry,
        )

        # Per-column drift score
        self.column_drift_score = Gauge(
            "ml_column_drift_score",
            "Drift score for individual columns",
            labels + ["column_name"],
            registry=self.registry,
        )

        # Model performance metrics
        self.model_accuracy = Gauge(
            "ml_model_accuracy",
            "Current model accuracy",
            labels,
            registry=self.registry,
        )

        self.model_f1_score = Gauge(
            "ml_model_f1_score",
            "Current model F1 score",
            labels,
            registry=self.registry,
        )

        self.model_precision = Gauge(
            "ml_model_precision",
            "Current model precision",
            labels,
            registry=self.registry,
        )

        self.model_recall = Gauge(
            "ml_model_recall",
            "Current model recall",
            labels,
            registry=self.registry,
        )

        self.performance_degradation = Gauge(
            "ml_performance_degradation_percent",
            "Performance degradation from reference (%)",
            labels,
            registry=self.registry,
        )

        # Health status (0=healthy, 1=warning, 2=critical)
        self.health_status = Gauge(
            "ml_model_health_status",
            "Model health status (0=healthy, 1=warning, 2=critical)",
            labels,
            registry=self.registry,
        )

        # Data quality metrics
        self.missing_values_share = Gauge(
            "ml_missing_values_share",
            "Share of missing values in current data",
            labels,
            registry=self.registry,
        )

        self.samples_analyzed = Counter(
            "ml_samples_analyzed_total",
            "Total samples analyzed for monitoring",
            labels,
            registry=self.registry,
        )

        # Monitoring run metrics
        self.monitoring_runs = Counter(
            "ml_monitoring_runs_total",
            "Total monitoring runs executed",
            labels + ["status"],
            registry=self.registry,
        )

        self.monitoring_duration = Histogram(
            "ml_monitoring_duration_seconds",
            "Duration of monitoring runs",
            labels,
            registry=self.registry,
        )


    def update_drift_metrics(self, drift_results: Dict[str, Any]):
        """
        Update Prometheus metrics from drift detection results.

        Args:
            drift_results: Results from DriftDetector.detect_data_drift()
        """
        labels = [self.model_name, self.model_version]

        # Dataset-level drift
        self.drift_detected.labels(*labels).set(
            1 if drift_results.get("dataset_drift", False) else 0
        )
        self.drift_share.labels(*labels).set(
            drift_results.get("drift_share", 0.0)
        )
        self.drifted_columns_count.labels(*labels).set(
            drift_results.get("number_of_drifted_columns", 0)
        )

        # Per-column drift scores
        for col, scores in drift_results.get("column_drift_scores", {}).items():
            self.column_drift_score.labels(*labels, col).set(
                scores.get("drift_score", 0.0)
            )

        # Missing values
        missing = drift_results.get("missing_values", {})
        self.missing_values_share.labels(*labels).set(
            missing.get("share_missing", 0.0)
        )

        logger.info("Updated drift metrics in Prometheus")

    def update_performance_metrics(self, perf_results: Dict[str, Any]):
        """
        Update Prometheus metrics from performance results.

        Args:
            perf_results: Results from ModelMonitor performance check
        """
        labels = [self.model_name, self.model_version]

        # Classification metrics
        if "current_accuracy" in perf_results:
            if perf_results.get("current_accuracy") is not None:
                self.model_accuracy.labels(*labels).set(
                    perf_results["current_accuracy"]
                )
            if perf_results.get("current_f1") is not None:
                self.model_f1_score.labels(*labels).set(
                    perf_results["current_f1"]
                )
            if perf_results.get("current_precision") is not None:
                self.model_precision.labels(*labels).set(
                    perf_results["current_precision"]
                )
            if perf_results.get("current_recall") is not None:
                self.model_recall.labels(*labels).set(
                    perf_results["current_recall"]
                )

        # Performance degradation
        if perf_results.get("performance_degradation") is not None:
            self.performance_degradation.labels(*labels).set(
                perf_results["performance_degradation"]
            )

        logger.info("Updated performance metrics in Prometheus")

    def update_from_monitoring_results(self, results: Dict[str, Any]):
        """
        Update all metrics from complete monitoring results.

        Args:
            results: Results from ModelMonitor.run_monitoring()
        """
        labels = [self.model_name, self.model_version]

        # Update drift metrics
        if "data_drift" in results:
            self.update_drift_metrics(results["data_drift"])

        # Update performance metrics
        if "model_performance" in results:
            self.update_performance_metrics(results["model_performance"])

        # Update health status
        health = results.get("health_status", "healthy")
        health_value = {"healthy": 0, "warning": 1, "critical": 2}.get(health, 0)
        self.health_status.labels(*labels).set(health_value)

        # Update counters
        self.samples_analyzed.labels(*labels).inc(
            results.get("samples_analyzed", 0)
        )
        self.monitoring_runs.labels(*labels, health).inc()

        logger.info(f"Updated all monitoring metrics. Health: {health}")

    def push_metrics(self, gateway_url: str, job_name: Optional[str] = None):
        """
        Push metrics to Prometheus Pushgateway.

        Args:
            gateway_url: URL of the Pushgateway
            job_name: Job name for grouping (defaults to model_name)
        """
        job = job_name or f"ml_monitoring_{self.model_name}"
        push_to_gateway(gateway_url, job=job, registry=self.registry)
        logger.info(f"Pushed metrics to gateway: {gateway_url}")

    def start_http_server(self, port: int = 8000):
        """
        Start HTTP server to expose metrics.

        Args:
            port: Port to expose metrics on
        """
        start_http_server(port, registry=self.registry)
        logger.info(f"Metrics server started on port {port}")

    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)
