import tempfile
from pathlib import Path

from mlflow import MlflowClient


def prepare_canary(workflow: str) -> str:
    client = MlflowClient()
    experiment = client.get_experiment_by_name("chaos-validation")
    experiment_id = (
        experiment.experiment_id if experiment else client.create_experiment("chaos-validation")
    )
    run = client.create_run(experiment_id, tags={"chaos.workflow": workflow})
    run_id = run.info.run_id
    client.log_param(run_id, "canary", workflow)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "canary.txt"
        path.write_text(workflow, encoding="utf-8")
        client.log_artifact(run_id, str(path))
    verify_canary(run_id, workflow, finish=False)
    return run_id


def verify_canary(run_id: str, workflow: str, finish: bool = True) -> None:
    client = MlflowClient()
    run = client.get_run(run_id)
    if run.data.params.get("canary") != workflow:
        raise ValueError("MLflow canary parameter was lost or changed")
    with tempfile.TemporaryDirectory() as directory:
        artifact = client.download_artifacts(run_id, "canary.txt", directory)
        if Path(artifact).read_text(encoding="utf-8") != workflow:
            raise ValueError("MLflow canary artifact was lost or changed")
    client.log_metric(run_id, "canary_verified", 1.0)
    if finish:
        client.set_terminated(run_id)
