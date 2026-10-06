from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.data.feature_engineering import FeatureEngineer
from src.pipelines.training_pipeline import TrainingPipeline


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_pipeline_fits_preprocessing_and_selection_only_on_training_data(task):
    pipeline = TrainingPipeline.__new__(TrainingPipeline)
    pipeline.config = pipeline._load_config(None)
    pipeline.config["model"]["type"] = task
    pipeline.config["preprocessing"]["feature_selection"]["k"] = 1
    pipeline.experiment_name = "isolation"
    pipeline.feature_engineer = FeatureEngineer()
    data = pd.DataFrame(
        {
            "a": np.arange(100, dtype=float),
            "b": np.arange(100, dtype=float) ** 2,
            "target": np.tile([0, 1], 50)
            if task == "classification"
            else np.arange(100, dtype=float),
        }
    )
    train, validation, test, _, _, _ = pipeline.split_data(data, data["target"])
    pipeline.load_data = MagicMock(return_value=data)
    pipeline.validate_data = MagicMock(return_value={"success": True})
    pipeline.train_model = MagicMock(return_value={"score": 1.0})
    pipeline.evaluate_model = MagicMock(return_value={"score": 1.0})
    pipeline.save_artifacts = MagicMock()
    with patch("src.pipelines.training_pipeline.mlflow"):
        result = pipeline.run_pipeline("unused.csv")
    scaler = pipeline.feature_engineer.preprocessor.named_transformers_["numeric"]
    np.testing.assert_allclose(scaler.mean_, train[["a", "b"]].mean().to_numpy())
    assert scaler.n_samples_seen_ == len(train)
    preprocessor = pipeline.feature_engineer.preprocessor
    selector = pipeline.feature_engineer.feature_selector
    train_x, train_y, validation_x, validation_y = pipeline.train_model.call_args.args
    test_x, test_y = pipeline.evaluate_model.call_args.args
    np.testing.assert_allclose(
        train_x,
        selector.transform(preprocessor.transform(train.drop(columns="target"))),
    )
    np.testing.assert_allclose(
        validation_x,
        selector.transform(preprocessor.transform(validation.drop(columns="target"))),
    )
    np.testing.assert_allclose(
        test_x, selector.transform(preprocessor.transform(test.drop(columns="target")))
    )
    assert train_y.index.equals(train.index)
    assert validation_y.index.equals(validation.index)
    assert test_y.index.equals(test.index)
    assert len(result["feature_names"]) == 1
