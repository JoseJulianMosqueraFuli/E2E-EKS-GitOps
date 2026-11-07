"""
Tests for model serving (src/pipelines/serving.py) and the served-prediction parity check.
"""

import json

import mlflow
import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient
from mlflow.exceptions import MlflowException
from sklearn.datasets import make_classification

from src.cli import main
from src.pipelines import serving, steps, validation

MODEL_NAME = "serving-model"


@pytest.fixture
def mlflow_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path}/mlflow.db")
    yield tmp_path
    mlflow.set_tracking_uri(previous)


@pytest.fixture
def frame():
    X, y = make_classification(
        n_samples=200, n_features=5, n_informative=3, n_classes=2, random_state=1
    )
    df = pd.DataFrame(X, columns=[f"num_{i}" for i in range(X.shape[1])])
    df["segment"] = np.where(X[:, 0] > 0, "high", "low")
    df["target"] = y
    return df


@pytest.fixture
def champion(mlflow_tmp, frame):
    data = mlflow_tmp / "train.csv"
    frame.to_csv(data, index=False)
    model_uri, _ = steps.train(
        str(data),
        MODEL_NAME,
        "serving-tests",
        "target",
        "classification",
        params={"n_estimators": 10},
    )
    version = steps.register(model_uri, MODEL_NAME)
    return {"data": str(data), "version": version}


def _payload(features: pd.DataFrame) -> dict:
    split = json.loads(features.to_json(orient="split"))
    split.pop("index", None)
    return {"dataframe_split": split}


class TestServing:
    def test_serves_the_champion_with_offline_predictions(self, champion, frame):
        app, version = serving.build_app(MODEL_NAME)
        features = frame.drop(columns=["target"]).head(5)
        expected = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion").predict(features)

        with TestClient(app) as client:
            assert client.get("/ping").status_code == 200
            response = client.post("/invocations", json=_payload(features))

        assert version == champion["version"]
        assert response.status_code == 200
        assert response.json()["predictions"] == expected.tolist()
        assert response.headers[serving.MODEL_NAME_HEADER] == MODEL_NAME
        assert response.headers[serving.MODEL_VERSION_HEADER] == version

    def test_rejects_input_that_does_not_match_the_signature(self, champion, frame):
        app, _ = serving.build_app(MODEL_NAME)
        features = frame.drop(columns=["target", "segment"]).head(2)

        with TestClient(app) as client:
            response = client.post("/invocations", json=_payload(features))

        assert response.status_code == 400

    def test_unknown_alias_fails_at_startup(self, champion):
        with pytest.raises(MlflowException):
            serving.build_app(MODEL_NAME, alias="missing")

    def test_serve_command_passes_options(self, monkeypatch):
        calls = []
        monkeypatch.setattr(serving, "serve", lambda *args: calls.append(args))

        result = CliRunner().invoke(
            main, ["step", "serve", "--model-name", MODEL_NAME, "--port", "9090"]
        )

        assert result.exit_code == 0, result.output
        assert calls == [(MODEL_NAME, "champion", "0.0.0.0", 9090)]


class FakeResponse:
    def __init__(self, status_code, body, headers):
        self.status_code = status_code
        self._body = body
        self.headers = headers

    def raise_for_status(self):
        assert self.status_code == 200, self._body

    def json(self):
        return self._body


def _unchanged(body):
    return body


def _flipped(body):
    return {"predictions": [1 - value for value in body["predictions"]]}


class TestDeploymentParity:
    def _route_to(self, monkeypatch, client, transform=_unchanged, versions=()):
        reported = iter(versions)

        def post(url, json, timeout):
            response = client.post("/invocations", json=json)
            headers = dict(response.headers)
            headers[serving.MODEL_VERSION_HEADER] = next(
                reported, headers[serving.MODEL_VERSION_HEADER]
            )
            return FakeResponse(response.status_code, transform(response.json()), headers)

        monkeypatch.setattr(validation.requests, "post", post)
        monkeypatch.setattr(validation.time, "sleep", lambda seconds: None)

    def test_accepts_predictions_that_match_the_registry(self, champion, monkeypatch):
        app, _ = serving.build_app(MODEL_NAME)
        with TestClient(app) as client:
            self._route_to(monkeypatch, client)
            validation.validate_deployment(
                "http://model/invocations",
                champion["data"],
                "target",
                timeout=5,
                model_uri=f"models:/{MODEL_NAME}@champion",
            )

    def test_rejects_predictions_that_differ_from_the_registry(self, champion, monkeypatch):
        app, _ = serving.build_app(MODEL_NAME)
        with TestClient(app) as client:
            self._route_to(monkeypatch, client, _flipped)
            with pytest.raises(ValueError, match="differ"):
                validation.validate_deployment(
                    "http://model/invocations",
                    champion["data"],
                    "target",
                    timeout=5,
                    model_uri=f"models:/{MODEL_NAME}@champion",
                )

    def test_waits_until_the_rollout_serves_the_expected_version(self, champion, monkeypatch):
        app, version = serving.build_app(MODEL_NAME)
        with TestClient(app) as client:
            self._route_to(monkeypatch, client, versions=["0", "0"])
            validation.validate_deployment(
                "http://model/invocations",
                champion["data"],
                "target",
                timeout=5,
                model_uri=f"models:/{MODEL_NAME}/{version}",
                expected_version=version,
            )

    def test_fails_when_the_expected_version_is_never_served(self, champion, monkeypatch):
        app, _ = serving.build_app(MODEL_NAME)
        with TestClient(app) as client:
            self._route_to(monkeypatch, client)
            with pytest.raises(RuntimeError) as error:
                validation.validate_deployment(
                    "http://model/invocations",
                    champion["data"],
                    "target",
                    timeout=0,
                    expected_version="99",
                )
        assert "not 99" in str(error.value.__cause__)

    def test_validate_command_passes_version_and_timeout(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            validation, "validate_deployment", lambda *args, **kwargs: calls.append(kwargs)
        )

        result = CliRunner().invoke(
            main,
            [
                "step",
                "validate-deployment",
                "--url",
                "http://model/invocations",
                "--data-uri",
                "data.csv",
                "--expected-version",
                "3",
                "--timeout",
                "60",
            ],
        )

        assert result.exit_code == 0, result.output
        assert calls == [{"timeout": 60, "model_uri": None, "expected_version": "3"}]

    @pytest.mark.parametrize(
        "served, expected, same",
        [
            ([0, 1, 1], np.array([0, 1, 1]), True),
            ([0.5, 1.25], np.array([0.5, 1.25 + 1e-9]), True),
            ([0, 1], np.array([1, 1]), False),
            (["a", "b"], np.array(["a", "b"]), True),
            ([0, 1], np.array([0, 1, 1]), False),
        ],
    )
    def test_prediction_comparison(self, served, expected, same):
        assert validation._same_predictions(served, expected) is same


class TestAliases:
    def _register(self, mlflow_tmp, frame):
        data = mlflow_tmp / "train.csv"
        frame.to_csv(data, index=False)
        model_uri, _ = steps.train(
            str(data),
            MODEL_NAME,
            "alias-tests",
            "target",
            "classification",
            params={"n_estimators": 5},
        )
        return model_uri

    def _register_cmd(self, model_uri, outputs):
        return CliRunner().invoke(
            main,
            [
                "step",
                "register",
                "--model-uri",
                model_uri,
                "--model-name",
                MODEL_NAME,
                "--outputs-dir",
                str(outputs),
            ],
        )

    def test_register_reports_the_version_it_replaces(self, mlflow_tmp, frame):
        model_uri = self._register(mlflow_tmp, frame)
        outputs = mlflow_tmp / "outputs"

        first = self._register_cmd(model_uri, outputs)
        assert first.exit_code == 0, first.output
        assert (outputs / "previous-version.txt").read_text() == ""

        second = self._register_cmd(model_uri, outputs)
        assert second.exit_code == 0, second.output
        assert (outputs / "model-version.txt").read_text() == "2"
        assert (outputs / "previous-version.txt").read_text() == "1"

    def test_set_alias_moves_back_and_removes(self, mlflow_tmp, frame):
        model_uri = self._register(mlflow_tmp, frame)
        steps.register(model_uri, MODEL_NAME)
        steps.register(model_uri, MODEL_NAME)
        assert steps.alias_version(MODEL_NAME) == "2"

        result = CliRunner().invoke(
            main, ["step", "set-alias", "--model-name", MODEL_NAME, "--version", "1"]
        )
        assert result.exit_code == 0, result.output
        assert steps.alias_version(MODEL_NAME) == "1"

        result = CliRunner().invoke(main, ["step", "set-alias", "--model-name", MODEL_NAME])
        assert result.exit_code == 0, result.output
        assert steps.alias_version(MODEL_NAME) is None
