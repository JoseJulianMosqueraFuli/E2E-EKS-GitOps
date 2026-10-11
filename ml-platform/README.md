# ML platform

Python components for training, inference, feature management, data validation and model monitoring.
Requires Python 3.10–3.12.

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

## Pipeline steps (`src.cli step`)

Each Argo task runs one step inside the `mlops-platform` image. Inputs and outputs are URIs
(local paths or `s3://`); outputs for Argo are written as files in `--outputs-dir`.

| Command | Does | Writes |
|---------|------|--------|
| `step split` | Splits raw data into train/test Parquet (stratified for classification) | `features-path.txt`, `test-data-path.txt` |
| `step train` | Fits preprocessing + model as one sklearn pipeline, logs it to MLflow | `model-uri.txt`, `run-id.txt` |
| `step evaluate` | Scores the candidate on held-out data; approves only if it reaches `--min-score` and beats `@champion` by `--min-improvement` | `model-approved.txt`, `evaluation-metrics.json` |
| `step register` | Registers the approved model and points `@champion` to it | `model-version.txt` |

The same code runs locally, on kind with MinIO (`AWS_ENDPOINT_URL`, `MLFLOW_S3_ENDPOINT_URL`) and on EKS
with IRSA. Implementation: `src/pipelines/steps.py`; tests: `tests/test_steps.py`.

## Container images

| File | Image | Notes |
|------|-------|-------|
| `Dockerfile` | `mlops-platform` | Stages `builder` (core deps from `poetry.lock`), `test` (all extras + pytest), `runtime` (non-root UID 8737, read-only root filesystem compatible) |
| `Dockerfile.mlflow-server` | `mlflow-server` | MLflow 2.22.5 + psycopg2 + boto3 (the official image has no PostgreSQL/S3 drivers), UID 1000 |
| `Dockerfile.monitoring` | monitoring service | Out of date (missing `requirements.txt`, old Evidently pin); tracked in `backlog.md` |

CI (`.github/workflows/ml-platform-image.yml`) runs the `test` stage and publishes `runtime` to GHCR for
`linux/amd64` with `sha-` tags. On EKS the manifests pull from ECR (`mlops-<env>-trainer`).

See [the ML platform guide](../docs/ml-platform-guide.md) for configuration and pipeline usage.
Infrastructure and cluster deployment are managed from the repository root.
