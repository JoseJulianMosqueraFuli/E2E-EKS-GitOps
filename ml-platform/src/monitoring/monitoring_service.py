"""
Model Monitoring Service

FastAPI service for running model monitoring as a Kubernetes service.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from .model_monitor import ModelMonitor
from .metrics_exporter import MetricsExporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Model Monitoring Service",
    description="Detects data drift and model drift using Evidently",
    version="1.0.0",
)

# Global state
monitors: Dict[str, ModelMonitor] = {}
exporters: Dict[str, MetricsExporter] = {}
reference_datasets: Dict[str, pd.DataFrame] = {}


class RegisterModelRequest(BaseModel):
    """Request to register a model for monitoring."""
    model_name: str
    model_version: str = "1.0"
    model_type: str = "classification"
    target_column: str = "target"
    prediction_column: str = "prediction"
    feature_columns: Optional[List[str]] = None
    reference_data_path: str


class MonitoringRequest(BaseModel):
    """Request to run monitoring on current data."""
    model_name: str
    current_data_path: Optional[str] = None
    current_data: Optional[List[Dict[str, Any]]] = None
    include_performance: bool = True
    generate_report: bool = False


class DriftCheckRequest(BaseModel):
    """Request for quick drift check."""
    model_name: str
    current_data: List[Dict[str, Any]]
    columns: Optional[List[str]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    registered_models: List[str]


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        registered_models=list(monitors.keys()),
    )


@app.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest, REGISTRY
    return generate_latest(REGISTRY)


@app.post("/models/register")
async def register_model(request: RegisterModelRequest):
    """Register a model for monitoring."""
    try:
        # Load reference data
        if request.reference_data_path.endswith(".csv"):
            reference_data = pd.read_csv(request.reference_data_path)
        elif request.reference_data_path.endswith(".parquet"):
            reference_data = pd.read_parquet(request.reference_data_path)
        else:
            raise HTTPException(400, "Unsupported file format")

        # Create monitor
        monitor = ModelMonitor(
            reference_data=reference_data,
            model_type=request.model_type,
            target_column=request.target_column,
            prediction_column=request.prediction_column,
            feature_columns=request.feature_columns,
        )

        # Create metrics exporter
        exporter = MetricsExporter(
            model_name=request.model_name,
            model_version=request.model_version,
        )

        # Store
        model_key = f"{request.model_name}:{request.model_version}"
        monitors[model_key] = monitor
        exporters[model_key] = exporter
        reference_datasets[model_key] = reference_data

        logger.info("Registered model: %s", model_key)

        return {
            "status": "registered",
            "model_key": model_key,
            "reference_samples": len(reference_data),
            "features": monitor.feature_columns,
        }

    except Exception as e:
        logger.error("Failed to register model: %s", e)
        raise HTTPException(500, str(e)) from e


@app.post("/monitoring/run")
async def run_monitoring(
    request: MonitoringRequest,
    background_tasks: BackgroundTasks,
):
    """Run comprehensive monitoring check."""
    model_key = _find_model_key(request.model_name)
    if not model_key:
        raise HTTPException(404, f"Model not found: {request.model_name}")

    monitor = monitors[model_key]
    exporter = exporters[model_key]

    try:
        # Load current data
        if request.current_data_path:
            if request.current_data_path.endswith(".csv"):
                current_data = pd.read_csv(request.current_data_path)
            else:
                current_data = pd.read_parquet(request.current_data_path)
        elif request.current_data:
            current_data = pd.DataFrame(request.current_data)
        else:
            raise HTTPException(400, "No current data provided")

        # Run monitoring
        results = monitor.run_monitoring(
            current_data=current_data,
            include_performance=request.include_performance,
        )

        # Update Prometheus metrics
        exporter.update_from_monitoring_results(results)

        # Generate report in background if requested
        if request.generate_report:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            model_key_safe = model_key.replace(':', '_')
            report_path = f"/tmp/reports/{model_key_safe}_{timestamp}.html"
            background_tasks.add_task(
                monitor.generate_monitoring_report,
                current_data,
                report_path,
            )
            results["report_path"] = report_path

        return results

    except Exception as e:
        logger.error("Monitoring failed: %s", e)
        raise HTTPException(500, str(e)) from e


@app.post("/drift/check")
async def check_drift(request: DriftCheckRequest):
    """Quick drift check without full monitoring."""
    model_key = _find_model_key(request.model_name)
    if not model_key:
        raise HTTPException(404, f"Model not found: {request.model_name}")

    monitor = monitors[model_key]
    exporter = exporters[model_key]

    try:
        current_data = pd.DataFrame(request.current_data)

        results = monitor.drift_detector.detect_data_drift(
            current_data=current_data,
            columns=request.columns,
        )

        # Update drift metrics
        exporter.update_drift_metrics(results)

        return results

    except Exception as e:
        logger.error("Drift check failed: %s", e)
        raise HTTPException(500, str(e)) from e


@app.get("/models/{model_name}/history")
async def get_monitoring_history(model_name: str):
    """Get monitoring history for a model."""
    model_key = _find_model_key(model_name)
    if not model_key:
        raise HTTPException(404, f"Model not found: {model_name}")

    return {
        "model_key": model_key,
        "history": monitors[model_key].get_monitoring_history(),
    }


@app.get("/models")
async def list_models():
    """List all registered models."""
    return {
        "models": [
            {
                "model_key": key,
                "model_type": monitors[key].model_type,
                "features_count": len(monitors[key].feature_columns),
                "reference_samples": len(reference_datasets[key]),
            }
            for key in monitors.keys()
        ]
    }


@app.delete("/models/{model_name}")
async def unregister_model(model_name: str):
    """Unregister a model from monitoring."""
    model_key = _find_model_key(model_name)
    if not model_key:
        raise HTTPException(404, f"Model not found: {model_name}")

    del monitors[model_key]
    del exporters[model_key]
    del reference_datasets[model_key]

    return {"status": "unregistered", "model_key": model_key}


def _find_model_key(model_name: str) -> Optional[str]:
    """Find model key by name (with or without version)."""
    if model_name in monitors:
        return model_name
    for key in monitors.keys():
        if key.startswith(f"{model_name}:"):
            return key
    return None


def create_app():
    """Factory function for creating the app."""
    return app


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
