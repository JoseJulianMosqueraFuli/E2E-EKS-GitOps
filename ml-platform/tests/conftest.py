"""
Shared pytest fixtures and configuration for the MLOps platform test suite.
"""

import os
import sys
import tempfile
import pytest
import pandas as pd
import numpy as np
from sklearn.datasets import make_classification, make_regression

# Ensure src is on the path when running tests directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(scope='session')
def sample_classification_data():
    """Generate a sample classification dataset."""
    X, y = make_classification(
        n_samples=200,
        n_features=10,
        n_informative=5,
        n_classes=2,
        random_state=42
    )
    feature_names = [f'feature_{i}' for i in range(X.shape[1])]
    data = pd.DataFrame(X, columns=feature_names)
    data['target'] = y
    return data


@pytest.fixture(scope='session')
def sample_regression_data():
    """Generate a sample regression dataset."""
    X, y = make_regression(
        n_samples=200,
        n_features=10,
        n_informative=5,
        noise=0.1,
        random_state=42
    )
    feature_names = [f'feature_{i}' for i in range(X.shape[1])]
    data = pd.DataFrame(X, columns=feature_names)
    data['target'] = y
    return data


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory simulating a project workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for subdir in ('data', 'config', 'logs', 'artifacts', 'models'):
            os.makedirs(os.path.join(tmpdir, subdir), exist_ok=True)
        yield tmpdir


@pytest.fixture(autouse=True)
def cleanup_mlflow():
    """Ensure no active MLflow runs leak between tests."""
    import mlflow
    yield
    mlflow.end_run()


@pytest.fixture
def mock_mlflow_tracking_uri(monkeypatch):
    """Set a temporary MLflow tracking URI to avoid polluting the local filesystem."""
    with tempfile.TemporaryDirectory() as tmpdir:
        uri = f"file://{tmpdir}/mlruns"
        monkeypatch.setenv('MLFLOW_TRACKING_URI', uri)
        yield uri
