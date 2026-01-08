"""
Drift Check Runner

Script executed by CronJob to run drift detection on all registered models.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DriftCheckRunner:
    """Runs drift checks for all configured models."""

    def __init__(
        self,
        monitoring_service_url: str,
        config_path: str = "/app/config/models.yaml",
    ):
        self.monitoring_service_url = monitoring_service_url.rstrip("/")
        self.config_path = config_path
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.results: List[Dict[str, Any]] = []

    def load_config(self) -> Dict[str, Any]:
        """Load models configuration."""
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        return {"models": [], "settings": {}}

    def run_all_checks(self):
        """Run drift checks for all configured models."""
        config = self.load_config()
        models = config.get("models", [])
        settings = config.get("settings", {})

        logger.info(f"Starting drift checks for {len(models)} models")

        for model_config in models:
            try:
                result = self.check_model(model_config, settings)
                self.results.append(result)

                # Alert if critical
                if result.get("health_status") == "critical":
                    self.send_alert(result)

            except Exception as e:
                logger.error(f"Failed to check model {model_config.get('name')}: {e}")
                self.results.append({
                    "model_name": model_config.get("name"),
                    "status": "error",
                    "error": str(e),
                })

        self.generate_summary()

    def check_model(
        self,
        model_config: Dict[str, Any],
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run drift check for a single model."""
        model_name = model_config["name"]
        logger.info(f"Checking model: {model_name}")

        # Load current data
        current_data = self.load_current_data(model_config)
        if current_data is None or len(current_data) == 0:
            logger.warning(f"No current data for model: {model_name}")
            return {
                "model_name": model_name,
                "status": "skipped",
                "reason": "no_current_data",
            }

        # Call monitoring service
        response = requests.post(
            f"{self.monitoring_service_url}/monitoring/run",
            json={
                "model_name": model_name,
                "current_data": current_data.to_dict(orient="records"),
                "include_performance": True,
                "generate_report": settings.get("generate_reports", True),
            },
            timeout=300,
        )

        if response.status_code != 200:
            raise Exception(f"Monitoring service error: {response.text}")

        result = response.json()
        result["model_name"] = model_name
        result["status"] = "completed"

        logger.info(
            f"Model {model_name}: health={result.get('health_status')}, "
            f"drift={result.get('data_drift', {}).get('dataset_drift')}"
        )

        return result

    def load_current_data(
        self,
        model_config: Dict[str, Any],
    ) -> Optional[pd.DataFrame]:
        """Load current production data for a model."""
        # Try S3 path first
        current_data_path = model_config.get("current_data_path")
        if current_data_path:
            if current_data_path.startswith("s3://"):
                return pd.read_parquet(current_data_path)
            elif current_data_path.endswith(".csv"):
                return pd.read_csv(current_data_path)
            elif current_data_path.endswith(".parquet"):
                return pd.read_parquet(current_data_path)

        # Try database query
        query = model_config.get("current_data_query")
        if query:
            return self.execute_query(query)

        return None

    def execute_query(self, query: str) -> Optional[pd.DataFrame]:
        """Execute SQL query to get current data."""
        # Placeholder - implement based on your data warehouse
        logger.warning("Database query not implemented")
        return None


    def send_alert(self, result: Dict[str, Any]):
        """Send alert for critical drift detection."""
        if not self.slack_webhook:
            logger.warning("Slack webhook not configured, skipping alert")
            return

        model_name = result.get("model_name", "unknown")
        health = result.get("health_status", "unknown")
        drift_data = result.get("data_drift", {})

        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 Model Drift Alert: {model_name}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Health Status:*\n{health.upper()}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Drift Detected:*\n{drift_data.get('dataset_drift', False)}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Drift Share:*\n{drift_data.get('drift_share', 0):.1%}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Drifted Columns:*\n{len(drift_data.get('drifted_columns', []))}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Drifted Features:*\n`{', '.join(drift_data.get('drifted_columns', [])[:5])}`",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Detected at {datetime.utcnow().isoformat()}Z",
                        },
                    ],
                },
            ],
        }

        try:
            response = requests.post(
                self.slack_webhook,
                json=message,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Alert sent for model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def generate_summary(self):
        """Generate and log summary of all checks."""
        total = len(self.results)
        completed = sum(1 for r in self.results if r.get("status") == "completed")
        critical = sum(1 for r in self.results if r.get("health_status") == "critical")
        warning = sum(1 for r in self.results if r.get("health_status") == "warning")
        healthy = sum(1 for r in self.results if r.get("health_status") == "healthy")
        errors = sum(1 for r in self.results if r.get("status") == "error")

        summary = f"""
========================================
DRIFT CHECK SUMMARY
========================================
Total Models: {total}
Completed: {completed}
  - Healthy: {healthy}
  - Warning: {warning}
  - Critical: {critical}
Errors: {errors}
========================================
"""
        logger.info(summary)

        # Save results to file
        output_path = f"/data/reports/drift_check_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"Results saved to: {output_path}")


def main():
    """Main entry point."""
    monitoring_url = os.getenv(
        "MONITORING_SERVICE_URL",
        "http://evidently-monitoring.ml-monitoring:8080",
    )
    config_path = os.getenv(
        "CONFIG_PATH",
        "/app/config/models.yaml",
    )

    runner = DriftCheckRunner(
        monitoring_service_url=monitoring_url,
        config_path=config_path,
    )

    try:
        runner.run_all_checks()
    except Exception as e:
        logger.error(f"Drift check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
