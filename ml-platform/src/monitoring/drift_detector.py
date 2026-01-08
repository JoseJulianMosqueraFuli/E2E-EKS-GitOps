"""
Drift Detector Module

Detects data drift and model drift using Evidently AI.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from evidently import ColumnMapping
from evidently.metric_preset import (
    DataDriftPreset,
    DataQualityPreset,
    TargetDriftPreset,
)
from evidently.metrics import (
    ColumnDriftMetric,
    DatasetDriftMetric,
    DatasetMissingValuesMetric,
)
from evidently.report import Report
from evidently.test_preset import DataDriftTestPreset, DataQualityTestPreset
from evidently.test_suite import TestSuite

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detects data drift between reference and current datasets."""

    def __init__(
        self,
        reference_data: pd.DataFrame,
        column_mapping: Optional[ColumnMapping] = None,
        drift_threshold: float = 0.05,
    ):
        """
        Initialize drift detector.

        Args:
            reference_data: Reference/baseline dataset
            column_mapping: Evidently column mapping configuration
            drift_threshold: P-value threshold for drift detection
        """
        self.reference_data = reference_data
        self.column_mapping = column_mapping or ColumnMapping()
        self.drift_threshold = drift_threshold
        self._last_report: Optional[Report] = None
        self._last_results: Optional[Dict[str, Any]] = None

    def detect_data_drift(
        self,
        current_data: pd.DataFrame,
        columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Detect data drift between reference and current data.

        Args:
            current_data: Current production data
            columns: Specific columns to check (None = all)

        Returns:
            Dictionary with drift detection results
        """
        logger.info("Running data drift detection...")

        # Build report with drift metrics
        report = Report(metrics=[
            DatasetDriftMetric(),
            DatasetMissingValuesMetric(),
        ])

        # Add per-column drift if specific columns requested
        if columns:
            for col in columns:
                if col in current_data.columns:
                    report.metrics.append(ColumnDriftMetric(column_name=col))

        report.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping,
        )

        self._last_report = report
        results = self._parse_drift_report(report)
        self._last_results = results

        logger.info(f"Data drift detected: {results['dataset_drift']}")
        return results


    def _parse_drift_report(self, report: Report) -> Dict[str, Any]:
        """Parse Evidently report into structured results."""
        report_dict = report.as_dict()
        metrics = report_dict.get("metrics", [])

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "dataset_drift": False,
            "drift_share": 0.0,
            "drifted_columns": [],
            "column_drift_scores": {},
            "missing_values": {},
        }

        for metric in metrics:
            metric_id = metric.get("metric", "")
            result = metric.get("result", {})

            if "DatasetDriftMetric" in metric_id:
                results["dataset_drift"] = result.get("dataset_drift", False)
                results["drift_share"] = result.get("drift_share", 0.0)
                results["number_of_drifted_columns"] = result.get(
                    "number_of_drifted_columns", 0
                )

            elif "ColumnDriftMetric" in metric_id:
                col_name = result.get("column_name", "unknown")
                results["column_drift_scores"][col_name] = {
                    "drift_detected": result.get("drift_detected", False),
                    "drift_score": result.get("drift_score", 0.0),
                    "stattest_name": result.get("stattest_name", ""),
                }
                if result.get("drift_detected"):
                    results["drifted_columns"].append(col_name)

            elif "DatasetMissingValuesMetric" in metric_id:
                current = result.get("current", {})
                results["missing_values"] = {
                    "total_missing": current.get("number_of_missing_values", 0),
                    "share_missing": current.get("share_of_missing_values", 0.0),
                }

        return results

    def run_drift_tests(
        self,
        current_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Run drift test suite with pass/fail results.

        Args:
            current_data: Current production data

        Returns:
            Test results with pass/fail status
        """
        logger.info("Running drift test suite...")

        test_suite = TestSuite(tests=[
            DataDriftTestPreset(),
            DataQualityTestPreset(),
        ])

        test_suite.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping,
        )

        results = test_suite.as_dict()
        summary = results.get("summary", {})

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "all_passed": summary.get("all_passed", False),
            "total_tests": summary.get("total_tests", 0),
            "success_tests": summary.get("success_tests", 0),
            "failed_tests": summary.get("failed_tests", 0),
            "by_status": summary.get("by_status", {}),
        }

    def generate_report(
        self,
        current_data: pd.DataFrame,
        output_path: Optional[str] = None,
        include_quality: bool = True,
    ) -> str:
        """
        Generate comprehensive drift report.

        Args:
            current_data: Current production data
            output_path: Path to save HTML report
            include_quality: Include data quality metrics

        Returns:
            Path to generated report
        """
        presets = [DataDriftPreset()]
        if include_quality:
            presets.append(DataQualityPreset())

        if self.column_mapping.target:
            presets.append(TargetDriftPreset())

        report = Report(metrics=presets)
        report.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping,
        )

        if output_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = f"drift_report_{timestamp}.html"

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        report.save_html(output_path)

        logger.info(f"Drift report saved to: {output_path}")
        return output_path

    def get_last_results(self) -> Optional[Dict[str, Any]]:
        """Get results from last drift detection run."""
        return self._last_results
