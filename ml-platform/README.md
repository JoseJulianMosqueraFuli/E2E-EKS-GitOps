# ML platform

Python components for training, inference, feature management, data validation and model monitoring.
Requires Python 3.11–3.12.

## Local setup

Run from this directory:

```bash
poetry install -E dev            # or: python -m pip install -e '.[dev]'
poetry run python -m src.cli create-sample data/sample.csv --n-samples 1000
poetry run pytest tests/ -v
```

## Dependencies and extras

| Install target | Contents |
|----------------|----------|
| core (default) | pandas, numpy, scipy, scikit-learn, pyarrow, MLflow, boto3, click |
| `validation`   | Great Expectations (`src.cli validate`, `DataValidator`) |
| `monitoring`   | Evidently, prometheus-client, FastAPI, uvicorn (`src/monitoring`) |
| `features`     | Feast (`src/features`) |
| `dev`          | All extras above + pytest, black, flake8, isort, mypy |

`DataValidator` and `TrainingPipeline` are imported lazily, so the core install can run the pipeline steps
without the optional extras.
SQLAlchemy stays on 2.0 and Tenacity below 9 so the core and all extras resolve to a single compatible
version of each dependency, including Feast's Tenacity requirement.
Pillow is pinned to 13.0.0 in the lock and the standalone MLflow server image to fix
[CVE-2026-112403](https://github.com/python-pillow/Pillow/security/advisories/GHSA-8g5g-8vmr-9782).
This security update requires Python 3.11 or newer; all CI runners and Python images already use
3.11 or 3.12. Training and monitoring images install the same locked dependency.
MLflow models use the `skops` serialization format. Logging allows only the internal
`sklearn.tree._tree.Tree` type needed by the models fitted in this process; arbitrary types discovered in
external artifacts are not automatically trusted.

Keep the MLflow server image and deployment tags aligned with the client version in `poetry.lock`.
`MLFLOW_TRACKING_URI` must point to the tracking server root URL, without an `/api/2.0` suffix.
The training CLI writes `model-uri.txt` and `run-id.txt` only after model logging succeeds. If Argo
reports missing output files, inspect the preceding training exception: the previous client 3.17.1 /
server 2.22.5 mismatch returned 404 on `/api/2.0/mlflow/logged-models`. Both now use 3.17.1.

The server image also includes `src/pipelines/mlflow_bootstrap.py`, invoked by a Kubernetes init
container. It serializes fresh PostgreSQL schema initialization across replicas with an advisory lock
and rejects outdated existing schemas until an explicit, backed-up migration is performed. The server
uses one HTTP worker per pod; MLflow's internal job execution is disabled because pipelines run in Argo.
Resource budgets and the recovery procedure are in the
[platform runtime contract](../docs/architecture/platform-runtime-config.md#backup-and-recovery).

Feast uses entity-key serialization version 3. Existing local SQLite snapshots contain older keys and
timestamp storage: back them up and rematerialize current validated source data into a new online
database before switching. Updating the YAML alone does not migrate stored data. The tests create fresh
temporary stores and verify actual historical and online feature values. See
[Feast's key migration guide](https://github.com/feast-dev/feast/blob/master/docs/how-to-guides/entity-reserialization-of-from-v2-to-v3.md).

## Pipeline steps (`src.cli step`)

Each Argo task runs one step inside the `mlops-platform` image. Inputs and outputs are URIs
(local paths or `s3://`); outputs for Argo are written as files in `--outputs-dir`.

| Command | Does | Writes |
|---------|------|--------|
| `step split` | Splits raw data into train/test Parquet (stratified for classification) | `features-path.txt`, `test-data-path.txt` |
| `step train` | Fits preprocessing + model as one sklearn pipeline, logs it to MLflow | `model-uri.txt`, `run-id.txt` |
| `step evaluate` | Scores the candidate on held-out data; approves only if it reaches `--min-score` and beats `@champion` by `--min-improvement` | `model-approved.txt`, `evaluation-metrics.json` |
| `step register` | Registers the approved model and points `@champion` to it | `model-version.txt` |
| `step validate-data` | Checks the input dataset and writes the validated dataset | `validated-data.txt`, `validation-report.json` |
| `step validate-deployment` | Sends sample rows to the deployed model and checks predictions | Validation status |
| `step chaos-canary` | Creates or verifies an MLflow parameter and artifact across a fault | `canary-run-id.txt` during preparation |
| `step backup-db` / `step restore-db` | Backs up PostgreSQL to S3 or restores into a separate empty database | Backup key or restore status |
| `step notify` | Logs the deployment outcome and optionally sends the configured webhook | Notification status |

The same code runs locally, on kind with MinIO (`AWS_ENDPOINT_URL`, `MLFLOW_S3_ENDPOINT_URL`) and on EKS
with IRSA. Implementation: `src/pipelines/steps.py`; tests: `tests/test_steps.py`.

## Container images

| File | Image | Notes |
|------|-------|-------|
| `Dockerfile` | `mlops-platform` | Stages `builder` (core deps from `poetry.lock`), `test` (all extras + pytest, including Feast definitions and temporary test data), `runtime` (non-root UID 8737, read-only root filesystem compatible) |
| `Dockerfile.mlflow-server` | `mlflow-server` | MLflow 3.17.1 + psycopg2 + boto3, UID 1000; matches the locked client |
| `Dockerfile.monitoring` | monitoring service | Monitoring extra from `poetry.lock`, UID 8737, import and HTTP health checks |

CI (`.github/workflows/ml-platform-image.yml`) runs the `test` stage and publishes `runtime` to GHCR for
`linux/amd64` with `sha-` tags. On EKS the manifests pull from ECR (`mlops-<env>-trainer`).
The manual `publish-ecr.yml` workflow publishes the initial dev images through GitHub OIDC.
See the [configuration and recovery contract](../docs/architecture/platform-runtime-config.md) before
upgrading an existing MLflow database or running backup/restore.

See [the ML platform guide](../docs/ml-platform-guide.md) for configuration and pipeline usage.
Infrastructure and cluster deployment are managed from the repository root.
