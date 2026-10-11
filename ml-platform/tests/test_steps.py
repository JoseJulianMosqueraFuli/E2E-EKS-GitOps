"""
Tests for single-container pipeline steps (src/pipelines/steps.py) and the `step` CLI.
"""

import io
import json
import os

import mlflow
import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner
from sklearn.datasets import make_classification, make_regression

from src.cli import main
from src.pipelines import steps


@pytest.fixture
def mlflow_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path}/mlflow.db")
    yield tmp_path
    mlflow.set_tracking_uri(previous)


@pytest.fixture
def mixed_classification_df():
    X, y = make_classification(
        n_samples=300, n_features=6, n_informative=4, n_classes=2, random_state=0
    )
    df = pd.DataFrame(X, columns=[f"num_{i}" for i in range(X.shape[1])])
    df["segment"] = np.where(X[:, 0] > 0, "high", "low")
    df["target"] = y
    return df


@pytest.fixture
def raw_csv(tmp_path, mixed_classification_df):
    path = tmp_path / "raw" / "data.csv"
    path.parent.mkdir()
    mixed_classification_df.to_csv(path, index=False)
    return str(path)


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body):
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}


class TestTableIO:
    def test_local_roundtrip_csv_and_parquet(self, tmp_path, mixed_classification_df):
        for ext in ("csv", "parquet"):
            uri = str(tmp_path / "nested" / f"data.{ext}")
            steps.write_table(mixed_classification_df, uri)
            loaded = steps.read_table(uri)
            assert loaded.shape == mixed_classification_df.shape

    def test_s3_roundtrip_uses_boto3(self, monkeypatch, mixed_classification_df):
        fake = FakeS3()
        monkeypatch.setattr(steps.boto3, "client", lambda service: fake)
        uri = "s3://bucket/prefix/data.parquet"
        steps.write_table(mixed_classification_df, uri)
        assert ("bucket", "prefix/data.parquet") in fake.objects
        assert steps.read_table(uri).shape == mixed_classification_df.shape

    def test_unsupported_format_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Unsupported data format"):
            steps.read_table(str(tmp_path / "data.json"))


class TestSplit:
    def test_split_writes_stratified_train_and_test(self, tmp_path, raw_csv):
        train_uri, test_uri = steps.split_dataset(
            raw_csv, str(tmp_path / "out"), "target", "classification", test_size=0.2
        )
        train_df, test_df = steps.read_table(train_uri), steps.read_table(test_uri)
        assert len(train_df) == 240 and len(test_df) == 60
        assert abs(train_df["target"].mean() - test_df["target"].mean()) < 0.05

    def test_split_rejects_missing_target_column(self, tmp_path, raw_csv):
        with pytest.raises(ValueError, match="not found"):
            steps.split_dataset(raw_csv, str(tmp_path / "out"), "label", "classification")

    def test_split_rejects_null_targets(self, tmp_path, mixed_classification_df):
        df = mixed_classification_df.astype({"target": "float"})
        df.loc[0, "target"] = np.nan
        path = str(tmp_path / "nulls.csv")
        df.to_csv(path, index=False)
        with pytest.raises(ValueError, match="null target"):
            steps.split_dataset(path, str(tmp_path / "out"), "target", "classification")

    def test_split_rejects_unknown_task_type(self, tmp_path, raw_csv):
        with pytest.raises(ValueError, match="task_type"):
            steps.split_dataset(raw_csv, str(tmp_path / "out"), "target", "clustering")


class TestTrainEvaluateRegister:
    def _split(self, tmp_path, raw_csv):
        return steps.split_dataset(raw_csv, str(tmp_path / "out"), "target", "classification")

    def test_trained_model_serves_raw_input(self, mlflow_tmp, raw_csv):
        train_uri, test_uri = self._split(mlflow_tmp, raw_csv)
        model_uri, run_id = steps.train(
            train_uri, "clf", "exp", "target", "classification", params={"n_estimators": 20}
        )
        assert model_uri == f"runs:/{run_id}/model"

        raw = steps.read_table(test_uri).drop(columns=["target"])
        assert raw["segment"].dtype == object
        predictions = mlflow.pyfunc.load_model(model_uri).predict(raw)
        assert len(predictions) == len(raw)

    def test_first_model_is_approved_and_registered_as_champion(self, mlflow_tmp, raw_csv):
        train_uri, test_uri = self._split(mlflow_tmp, raw_csv)
        model_uri, _ = steps.train(train_uri, "clf", "exp", "target", "classification")

        report = steps.evaluate(model_uri, test_uri, "clf", "target", "classification")
        assert report["approved"] is True
        assert report["champion"] is None
        assert {"accuracy", "f1_score", "roc_auc"} <= set(report["metrics"])

        assert steps.register(model_uri, "clf") == "1"
        client = mlflow.tracking.MlflowClient()
        assert client.get_model_version_by_alias("clf", "champion").version == "1"

    def test_candidate_must_beat_champion(self, mlflow_tmp, raw_csv):
        train_uri, test_uri = self._split(mlflow_tmp, raw_csv)
        champion_uri, _ = steps.train(train_uri, "clf", "exp", "target", "classification")
        steps.register(champion_uri, "clf")

        candidate_uri, _ = steps.train(
            train_uri,
            "clf",
            "exp",
            "target",
            "classification",
            algorithm="logistic_regression",
        )
        report = steps.evaluate(
            candidate_uri, test_uri, "clf", "target", "classification", min_improvement=0.5
        )
        assert report["approved"] is False
        assert report["champion"]["version"] == "1"
        assert any("does not beat champion" in r for r in report["reasons"])

    def test_min_score_blocks_promotion(self, mlflow_tmp, raw_csv):
        train_uri, test_uri = self._split(mlflow_tmp, raw_csv)
        model_uri, _ = steps.train(train_uri, "clf", "exp", "target", "classification")
        report = steps.evaluate(
            model_uri, test_uri, "clf", "target", "classification", min_score=1.01
        )
        assert report["approved"] is False
        assert "below min_score" in report["reasons"][0]

    def test_regression_flow(self, mlflow_tmp):
        X, y = make_regression(n_samples=200, n_features=5, noise=0.1, random_state=0)
        df = pd.DataFrame(X, columns=[f"f{i}" for i in range(5)])
        df["target"] = y
        raw = str(mlflow_tmp / "reg.csv")
        df.to_csv(raw, index=False)

        train_uri, test_uri = steps.split_dataset(
            raw, str(mlflow_tmp / "out"), "target", "regression"
        )
        model_uri, _ = steps.train(
            train_uri, "reg", "exp", "target", "regression", algorithm="linear_regression"
        )
        report = steps.evaluate(model_uri, test_uri, "reg", "target", "regression")
        assert report["primary_metric"] == "r2"
        assert report["metrics"]["r2"] > 0.9
        assert report["approved"] is True


class TestComputeMetrics:
    def test_multiclass_roc_auc_uses_probabilities(self):
        from sklearn.linear_model import LogisticRegression

        X, y = make_classification(
            n_samples=300, n_features=6, n_informative=4, n_classes=3, random_state=0
        )
        X = pd.DataFrame(X)
        model = LogisticRegression(max_iter=1000).fit(X, y)
        metrics = steps.compute_metrics("classification", model, X, pd.Series(y))
        assert 0.5 < metrics["roc_auc"] <= 1.0


class TestStepCLI:
    def test_full_step_sequence_writes_argo_outputs(self, mlflow_tmp, raw_csv):
        runner = CliRunner()
        outputs = mlflow_tmp / "argo"

        result = runner.invoke(
            main,
            [
                "step",
                "split",
                "--input",
                raw_csv,
                "--output",
                str(mlflow_tmp / "out"),
                "--outputs-dir",
                str(outputs),
            ],
        )
        assert result.exit_code == 0, result.output
        train_uri = (outputs / "features-path.txt").read_text()
        test_uri = (outputs / "test-data-path.txt").read_text()

        result = runner.invoke(
            main,
            [
                "step",
                "train",
                "--features",
                train_uri,
                "--model-name",
                "clf",
                "--experiment-name",
                "exp",
                "--params",
                json.dumps({"n_estimators": 10}),
                "--outputs-dir",
                str(outputs),
            ],
        )
        assert result.exit_code == 0, result.output
        model_uri = (outputs / "model-uri.txt").read_text()
        assert model_uri.startswith("runs:/")
        assert (outputs / "run-id.txt").read_text() in model_uri

        result = runner.invoke(
            main,
            [
                "step",
                "evaluate",
                "--model-uri",
                model_uri,
                "--test-data",
                test_uri,
                "--model-name",
                "clf",
                "--outputs-dir",
                str(outputs),
            ],
        )
        assert result.exit_code == 0, result.output
        assert (outputs / "model-approved.txt").read_text() == "true"
        report = json.loads((outputs / "evaluation-metrics.json").read_text())
        assert report["primary_metric"] == "f1_score"

        result = runner.invoke(
            main,
            [
                "step",
                "register",
                "--model-uri",
                model_uri,
                "--model-name",
                "clf",
                "--outputs-dir",
                str(outputs),
            ],
        )
        assert result.exit_code == 0, result.output
        assert (outputs / "model-version.txt").read_text() == "1"
        assert os.path.exists(outputs)
