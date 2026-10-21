from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.pipelines import chaos_probe


@pytest.fixture
def client(monkeypatch, tmp_path):
    client = Mock()
    client.get_run.return_value = SimpleNamespace(
        data=SimpleNamespace(params={"canary": "workflow"})
    )
    artifact = tmp_path / "canary.txt"
    artifact.write_text("workflow")
    client.download_artifacts.return_value = str(artifact)
    monkeypatch.setattr(chaos_probe, "MlflowClient", lambda: client)
    return client


def test_canary_round_trip(client):
    client.get_experiment_by_name.return_value = None
    client.create_experiment.return_value = "1"
    client.create_run.return_value = SimpleNamespace(info=SimpleNamespace(run_id="run"))
    assert chaos_probe.prepare_canary("workflow") == "run"
    client.log_param.assert_called_once_with("run", "canary", "workflow")
    client.log_artifact.assert_called_once()
    client.set_terminated.assert_not_called()
    chaos_probe.verify_canary("run", "workflow")
    client.set_terminated.assert_called_once_with("run")


@pytest.mark.parametrize("failure", ["parameter", "artifact", "missing-artifact"])
def test_canary_fails_on_data_loss(client, failure):
    if failure == "parameter":
        client.get_run.return_value.data.params = {}
    elif failure == "artifact":
        Path(client.download_artifacts.return_value).write_text("changed")
    else:
        client.download_artifacts.side_effect = FileNotFoundError("canary.txt")
    with pytest.raises((ValueError, FileNotFoundError)):
        chaos_probe.verify_canary("run", "workflow")
    client.set_terminated.assert_not_called()
    client.log_metric.assert_not_called()
