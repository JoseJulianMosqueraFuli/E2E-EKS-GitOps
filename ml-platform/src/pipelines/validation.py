import hashlib
import json
import logging
import os
import time
from typing import Dict, List, Optional

import numpy as np
import requests

from src.pipelines.serving import MODEL_VERSION_HEADER
from src.pipelines.steps import read_table, write_table

logger = logging.getLogger(__name__)


def validate_data(source: str, destination: str, target: str, suite: str) -> Dict:
    if suite not in ("default", "production"):
        raise ValueError("Unknown validation suite")
    frame = read_table(source)
    if frame.empty or target not in frame or len(frame.columns) < 2:
        raise ValueError("Data must contain rows, features and the target column")
    if frame[target].isna().any():
        raise ValueError("Target values cannot be missing")
    threshold = 0.01 if suite == "production" else 0.05
    if frame.isna().mean().max() > threshold:
        raise ValueError("Column null rate exceeds the validation policy")
    if frame.duplicated().mean() > threshold:
        raise ValueError("Duplicate row rate exceeds the validation policy")
    numeric = frame.select_dtypes(include="number").to_numpy()
    if np.isinf(numeric).any():
        raise ValueError("Numeric features cannot contain infinity")
    checksum = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
    output = f"{destination.rstrip('/')}/{checksum}/data.parquet"
    write_table(frame, output)
    return {
        "data_uri": output,
        "rows": len(frame),
        "columns": len(frame.columns),
        "sha256": checksum,
        "suite": suite,
    }


def _same_predictions(served, expected) -> bool:
    served = np.asarray(served).ravel()
    expected = np.asarray(expected).ravel()
    if served.shape != expected.shape:
        return False
    if np.issubdtype(served.dtype, np.number) and np.issubdtype(expected.dtype, np.number):
        return bool(np.allclose(served.astype(float), expected.astype(float), rtol=1e-6))
    return bool((served.astype(str) == expected.astype(str)).all())


def _request_predictions(
    url: str, frame, timeout: int, expected_version: Optional[str] = None
) -> List:
    payload = {"dataframe_split": json.loads(frame.to_json(orient="split"))}
    payload["dataframe_split"].pop("index", None)
    deadline = time.monotonic() + timeout
    last_error = None
    while True:
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            served = response.headers.get(MODEL_VERSION_HEADER)
            if expected_version and served != expected_version:
                raise ValueError(f"Endpoint serves version {served}, not {expected_version}")
            predictions = response.json().get("predictions")
            if not isinstance(predictions, list) or len(predictions) != len(frame):
                raise ValueError("Inference response must contain one prediction per input")
            if any(value is None for value in predictions):
                raise ValueError("Inference returned a missing prediction")
            return predictions
        except (requests.RequestException, ValueError) as error:
            last_error = error
        if time.monotonic() >= deadline:
            break
        time.sleep(2)
    raise RuntimeError("Inference validation did not succeed before the deadline") from last_error


def validate_deployment(
    url: str,
    data_uri: str,
    target: str,
    timeout: int = 300,
    model_uri: Optional[str] = None,
    expected_version: Optional[str] = None,
) -> None:
    if not url.startswith(("http://", "https://")):
        raise ValueError("Inference URL must use HTTP(S)")
    frame = read_table(data_uri).drop(columns=[target]).head(3)
    if frame.empty:
        raise ValueError("Inference validation requires data")
    predictions = _request_predictions(url, frame, timeout, expected_version)
    if expected_version:
        logger.info("Endpoint serves version %s", expected_version)
    if model_uri:
        import mlflow.pyfunc

        expected = mlflow.pyfunc.load_model(model_uri).predict(frame)
        if not _same_predictions(predictions, expected):
            raise ValueError(f"Served predictions differ from {model_uri}")
        logger.info("Served predictions match %s", model_uri)


def notify_pipeline(model: str, version: str, status: str) -> None:
    message = f"Model {model}, version {version}: {status}"
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if webhook:
        response = requests.post(webhook, json={"text": message}, timeout=10)
        response.raise_for_status()
    logger.info(message)
