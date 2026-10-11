"""
Pipeline Steps

Single-responsibility steps executed as separate containers by Argo Workflows.
Each step reads and writes data through URIs (local paths or s3://), so the same
code runs on a laptop, on kind with MinIO (AWS_ENDPOINT_URL) and on EKS with IRSA.
"""

import io
import logging
import os
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import boto3
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.exceptions import MlflowException
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from src.data.feature_engineering import FeatureEngineer
from src.models.classification_model import ClassificationModel
from src.models.regression_model import RegressionModel

logger = logging.getLogger(__name__)

TASK_TYPES = ("classification", "regression")
PRIMARY_METRIC = {"classification": "f1_score", "regression": "r2"}
MODEL_CLASSES = {"classification": ClassificationModel, "regression": RegressionModel}


def _split_s3_uri(uri: str) -> Tuple[str, str]:
    parsed = urlparse(uri)
    return parsed.netloc, parsed.path.lstrip("/")


def _format(uri: str) -> str:
    if uri.endswith(".parquet"):
        return "parquet"
    if uri.endswith(".csv"):
        return "csv"
    raise ValueError(f"Unsupported data format for {uri}: use .csv or .parquet")


def read_table(uri: str) -> pd.DataFrame:
    """Read a CSV or Parquet table from a local path or an s3:// URI."""
    fmt = _format(uri)
    if uri.startswith("s3://"):
        bucket, key = _split_s3_uri(uri)
        body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
        source: Any = io.BytesIO(body)
    else:
        source = uri
    df = pd.read_parquet(source) if fmt == "parquet" else pd.read_csv(source)
    logger.info("Read %s rows x %s columns from %s", df.shape[0], df.shape[1], uri)
    return df


def write_table(df: pd.DataFrame, uri: str) -> str:
    """Write a table to a local path or an s3:// URI and return the URI."""
    fmt = _format(uri)
    buffer = io.BytesIO()
    if fmt == "parquet":
        df.to_parquet(buffer, index=False)
    else:
        df.to_csv(buffer, index=False)
    if uri.startswith("s3://"):
        bucket, key = _split_s3_uri(uri)
        boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())
    else:
        os.makedirs(os.path.dirname(os.path.abspath(uri)), exist_ok=True)
        with open(uri, "wb") as f:
            f.write(buffer.getvalue())
    logger.info("Wrote %s rows to %s", len(df), uri)
    return uri


def _check_task_type(task_type: str) -> None:
    if task_type not in TASK_TYPES:
        raise ValueError(f"task_type must be one of {TASK_TYPES}, got {task_type}")


def _features_and_target(df: pd.DataFrame, target: str) -> Tuple[pd.DataFrame, pd.Series]:
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found in {list(df.columns)}")
    return df.drop(columns=[target]), df[target]


def split_dataset(
    input_uri: str,
    output_prefix: str,
    target: str,
    task_type: str,
    test_size: float = 0.2,
    seed: int = 42,
) -> Tuple[str, str]:
    """Split raw data into train/test sets before any fitting, to avoid leakage."""
    _check_task_type(task_type)
    df = read_table(input_uri)
    _features_and_target(df, target)
    missing_target = int(df[target].isna().sum())
    if missing_target:
        raise ValueError(f"{missing_target} rows have a null target '{target}'")
    if len(df) < 10:
        raise ValueError(f"Need at least 10 rows to split, got {len(df)}")

    stratify = None
    if task_type == "classification" and df[target].value_counts().min() >= 2:
        stratify = df[target]
    train_df, test_df = train_test_split(
        df, test_size=test_size, random_state=seed, stratify=stratify
    )

    prefix = output_prefix.rstrip("/")
    train_uri = write_table(train_df, f"{prefix}/train.parquet")
    test_uri = write_table(test_df, f"{prefix}/test.parquet")
    return train_uri, test_uri


def build_pipeline(
    X: pd.DataFrame,
    task_type: str,
    algorithm: str,
    params: Dict[str, Any],
    experiment_name: str,
    numeric_strategy: str = "standard",
    categorical_strategy: str = "onehot",
) -> Pipeline:
    """Build preprocessing + estimator as one sklearn Pipeline, so serving gets raw input."""
    _check_task_type(task_type)
    numeric = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    preprocessor = FeatureEngineer().create_preprocessor(
        numeric_features=numeric,
        categorical_features=categorical,
        numeric_strategy=numeric_strategy,
        categorical_strategy=categorical_strategy,
    )
    model = MODEL_CLASSES[task_type](
        model_name=f"{algorithm}_{task_type}",
        algorithm=algorithm,
        experiment_name=experiment_name,
    )
    estimator = model.create_model(**params)
    return Pipeline([("preprocessor", preprocessor), ("model", estimator)])


def compute_metrics(task_type: str, model: Any, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
    """Compute evaluation metrics; ROC AUC uses probabilities, never hard labels."""
    _check_task_type(task_type)
    y_pred = model.predict(X)
    if task_type == "regression":
        return {
            "rmse": float(np.sqrt(mean_squared_error(y, y_pred))),
            "mae": float(mean_absolute_error(y, y_pred)),
            "r2": float(r2_score(y, y_pred)),
        }

    metrics = {
        "accuracy": float(accuracy_score(y, y_pred)),
        "precision": float(precision_score(y, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y, y_pred, average="weighted", zero_division=0)),
        "f1_score": float(f1_score(y, y_pred, average="weighted", zero_division=0)),
    }
    if hasattr(model, "predict_proba") and y.nunique() >= 2:
        proba = model.predict_proba(X)
        try:
            if proba.shape[1] == 2:
                metrics["roc_auc"] = float(roc_auc_score(y, proba[:, 1]))
            else:
                metrics["roc_auc"] = float(
                    roc_auc_score(y, proba, multi_class="ovr", labels=model.classes_)
                )
        except ValueError as e:
            logger.warning("Could not compute ROC AUC: %s", e)
    return metrics


def train(
    train_uri: str,
    model_name: str,
    experiment_name: str,
    target: str,
    task_type: str,
    algorithm: str = "random_forest",
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """Train a preprocessing + model pipeline and log it to MLflow (not registered)."""
    params = params or {}
    df = read_table(train_uri)
    X, y = _features_and_target(df, target)

    mlflow.set_experiment(experiment_name)
    pipeline = build_pipeline(X, task_type, algorithm, params, experiment_name)

    with mlflow.start_run(run_name=f"{model_name}-train") as run:
        mlflow.set_tags(
            {
                "model_name": model_name,
                "task_type": task_type,
                "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
                "image": os.environ.get("IMAGE_REF", "unknown"),
            }
        )
        mlflow.log_params(
            {
                "algorithm": algorithm,
                "train_data": train_uri,
                "train_rows": len(df),
                "n_features": X.shape[1],
                **{f"hp_{k}": v for k, v in params.items()},
            }
        )
        pipeline.fit(X, y)
        train_metrics = compute_metrics(task_type, pipeline, X, y)
        mlflow.log_metrics({f"train_{k}": v for k, v in train_metrics.items()})

        sample = X.head(5)
        signature = infer_signature(sample, pipeline.predict(sample))
        mlflow.sklearn.log_model(
            pipeline, artifact_path="model", signature=signature, input_example=sample
        )
        run_id = run.info.run_id

    model_uri = f"runs:/{run_id}/model"
    logger.info("Trained %s: %s (train metrics %s)", model_name, model_uri, train_metrics)
    return model_uri, run_id


def _champion(model_name: str, alias: str) -> Optional[Any]:
    try:
        return MlflowClient().get_model_version_by_alias(model_name, alias)
    except MlflowException:
        return None


def evaluate(
    model_uri: str,
    test_uri: str,
    model_name: str,
    target: str,
    task_type: str,
    min_score: float = 0.0,
    min_improvement: float = 0.0,
    alias: str = "champion",
) -> Dict[str, Any]:
    """
    Evaluate a candidate on held-out data and decide whether it can be promoted.

    The candidate must reach ``min_score`` on the primary metric and, if a model
    holds ``alias``, beat it by at least ``min_improvement`` on the same test set.
    """
    _check_task_type(task_type)
    primary = PRIMARY_METRIC[task_type]
    df = read_table(test_uri)
    X, y = _features_and_target(df, target)

    candidate = mlflow.sklearn.load_model(model_uri)
    metrics = compute_metrics(task_type, candidate, X, y)
    score = metrics[primary]

    reasons = []
    approved = True
    if score < min_score:
        approved = False
        reasons.append(f"{primary}={score:.4f} below min_score={min_score}")

    champion_report = None
    champion = _champion(model_name, alias)
    if champion is not None:
        champion_model = mlflow.sklearn.load_model(f"models:/{model_name}@{alias}")
        champion_metrics = compute_metrics(task_type, champion_model, X, y)
        champion_score = champion_metrics[primary]
        champion_report = {"version": str(champion.version), "metrics": champion_metrics}
        if score < champion_score + min_improvement:
            approved = False
            reasons.append(
                f"{primary}={score:.4f} does not beat {alias} v{champion.version} "
                f"({champion_score:.4f}) by {min_improvement}"
            )

    report = {
        "approved": approved,
        "primary_metric": primary,
        "metrics": metrics,
        "champion": champion_report,
        "thresholds": {"min_score": min_score, "min_improvement": min_improvement},
        "reasons": reasons,
        "test_data": test_uri,
    }

    if model_uri.startswith("runs:/"):
        run_id = model_uri.split("/")[1]
        with mlflow.start_run(run_id=run_id):
            mlflow.log_metrics({f"test_{k}": v for k, v in metrics.items()})
            mlflow.log_dict(report, "evaluation.json")
            mlflow.set_tag("approved", str(approved).lower())

    logger.info("Evaluation of %s: approved=%s %s", model_uri, approved, reasons)
    return report


def register(model_uri: str, model_name: str, alias: str = "champion") -> str:
    """Register an approved model version and point ``alias`` to it."""
    version = mlflow.register_model(model_uri, model_name).version
    MlflowClient().set_registered_model_alias(model_name, alias, version)
    logger.info("Registered %s v%s as @%s", model_name, version, alias)
    return str(version)


def write_outputs(outputs_dir: str, values: Dict[str, str]) -> None:
    """Write step outputs as files, the contract Argo uses for output parameters."""
    os.makedirs(outputs_dir, exist_ok=True)
    for name, value in values.items():
        with open(os.path.join(outputs_dir, name), "w") as f:
            f.write(value)
