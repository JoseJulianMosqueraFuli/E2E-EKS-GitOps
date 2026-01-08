"""
Model Monitor Module

Monitors model performance and detects model drift.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from evidently import ColumnMapping
from evidently.metric_preset import (
    ClassificationPreset,
    RegressionPreset,
)
from evidently.metrics import (
    ClassificationQualityMetric,
    RegressionQualityMetric,
)
from evidently.report import Report

from .drift_detector import DriftDetector

logger = logging.getLogger(__name__)


class ModelMonitor:
    """
    Comprehensive model monitoring combining drift detection
    and performance tracking.
    """

    def __init__(
        self,
        reference_data: pd.DataFrame,
        model_type: str = "classification",
        target_column: str = "target",
        prediction_column: str = "prediction",
        feature_columns: Optional[List[str]] = None,
        drift_threshold: float = 0.05,
    ):
        """
        Initialize model monitor.

        Args:
            reference_data: Reference dataset with features and predictions
            model_type: 'classification' or 'regression'
            target_column: Name of target column
            prediction_column: Name of prediction column
            feature_columns: List of feature columns to monitor
            drift_threshold: Threshold for drift detection
        """
        self.reference_data = reference_data
        self.model_type = model_type
        self.target_column = target_column
        self.prediction_column = prediction_column
        self.drift_threshold = drift_threshold

        # Determine feature columns
        if feature_columns:
            self.feature_columns = feature_columns
        else:
            exclude = {target_column, prediction_column}
            self.feature_columns = [
                c for c in reference_data.columns if c not in exclude
            ]

        # Setup column mapping
        self.column_mapping = ColumnMapping(
            target=target_column,
            prediction=prediction_column,
            numerical_features=[
                c for c in self.feature_columns
                if reference_data[c].dtype in ['int64', 'float64']
            ],
            categorical_features=[
                c for c in self.feature_columns
                if reference_data[c].dtype == 'object'
            ],
        )

        # Initialize drift detector
        self.drift_detector = DriftDetector(
            reference_data=reference_data,
            column_mapping=self.column_mapping,
            drift_threshold=drift_threshold,
        )

        self._monitoring_history: List[Dict[str, Any]] = []


    def run_monitoring(
        self,
        current_data: pd.DataFrame,
        include_performance: bool = True,
    ) -> Dict[str, Any]:
        """
        Run comprehensive monitoring check.

        Args:
            current_data: Current production data
            include_performance: Include model performance metrics

        Returns:
            Complete monitoring results
        """
        logger.info("Running model monitoring...")
        timestamp = datetime.utcnow().isoformat()

        results = {
            "timestamp": timestamp,
            "model_type": self.model_type,
            "samples_analyzed": len(current_data),
        }

        # Data drift detection
        drift_results = self.drift_detector.detect_data_drift(
            current_data=current_data,
            columns=self.feature_columns,
        )
        results["data_drift"] = drift_results

        # Model performance (if target available)
        if include_performance and self.target_column in current_data.columns:
            perf_results = self._check_model_performance(current_data)
            results["model_performance"] = perf_results

        # Determine overall health
        results["health_status"] = self._determine_health(results)

        # Store in history
        self._monitoring_history.append(results)

        logger.info(f"Monitoring complete. Health: {results['health_status']}")
        return results

    def _check_model_performance(
        self,
        current_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Check model performance metrics."""
        if self.model_type == "classification":
            report = Report(metrics=[ClassificationQualityMetric()])
        else:
            report = Report(metrics=[RegressionQualityMetric()])

        report.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping,
        )

        report_dict = report.as_dict()
        metrics = report_dict.get("metrics", [{}])[0].get("result", {})

        if self.model_type == "classification":
            current = metrics.get("current", {})
            reference = metrics.get("reference", {})
            return {
                "current_accuracy": current.get("accuracy"),
                "current_precision": current.get("precision"),
                "current_recall": current.get("recall"),
                "current_f1": current.get("f1"),
                "reference_accuracy": reference.get("accuracy"),
                "reference_f1": reference.get("f1"),
                "performance_degradation": self._calc_degradation(
                    reference.get("f1", 0), current.get("f1", 0)
                ),
            }
        else:
            current = metrics.get("current", {})
            reference = metrics.get("reference", {})
            return {
                "current_rmse": current.get("rmse"),
                "current_mae": current.get("mae"),
                "current_r2": current.get("r2_score"),
                "reference_rmse": reference.get("rmse"),
                "reference_r2": reference.get("r2_score"),
                "performance_degradation": self._calc_degradation(
                    reference.get("r2_score", 0), current.get("r2_score", 0)
                ),
            }

    def _calc_degradation(self, ref: float, curr: float) -> float:
        """Calculate performance degradation percentage."""
        if ref == 0:
            return 0.0
        return ((ref - curr) / ref) * 100

    def _determine_health(self, results: Dict[str, Any]) -> str:
        """Determine overall model health status."""
        drift = results.get("data_drift", {})
        perf = results.get("model_performance", {})

        # Critical: significant drift detected
        if drift.get("dataset_drift", False):
            drift_share = drift.get("drift_share", 0)
            if drift_share > 0.5:
                return "critical"
            elif drift_share > 0.3:
                return "warning"

        # Check performance degradation
        degradation = perf.get("performance_degradation", 0)
        if degradation > 20:
            return "critical"
        elif degradation > 10:
            return "warning"

        return "healthy"

    def generate_monitoring_report(
        self,
        current_data: pd.DataFrame,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate comprehensive HTML monitoring report."""
        if self.model_type == "classification":
            presets = [ClassificationPreset()]
        else:
            presets = [RegressionPreset()]

        report = Report(metrics=presets)
        report.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping,
        )

        if output_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = f"monitoring_report_{timestamp}.html"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        report.save_html(output_path)

        logger.info(f"Monitoring report saved to: {output_path}")
        return output_path

    def get_monitoring_history(self) -> List[Dict[str, Any]]:
        """Get historical monitoring results."""
        return self._monitoring_history

    def export_metrics_json(self, output_path: str) -> str:
        """Export latest metrics as JSON for external systems."""
        if not self._monitoring_history:
            raise ValueError("No monitoring data available")

        latest = self._monitoring_history[-1]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(latest, f, indent=2)

        return output_path
