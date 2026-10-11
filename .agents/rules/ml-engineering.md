---
description: ML engineering practices for data, training, evaluation, tracking and monitoring code
globs: ml-platform/**
---

# ML Engineering

Read the ML architecture rule for the overall lifecycle; this rule covers implementation.

## Data

- Validate data at every boundary (`src/data/data_validator.py`): schema, types, ranges, null rates, row counts, duplicates. Fail the pipeline on violations instead of silently cleaning.
- Split before any fitting (scalers, encoders, imputers) to avoid leakage. Time-dependent data uses time-based splits.
- Version datasets (S3 path with snapshot/date or content hash) and log the version to MLflow.
- Feature logic lives in one place (`src/data/feature_engineering.py` or Feast feature views) and is reused by training and inference.

## Training

- Deterministic: set seeds (numpy, random, framework), pin library versions, record them.
- Log to MLflow for every run: params, metrics, data version, git commit, feature list, model signature and input example, environment (`poetry.lock` or requirements).
- Models implement the base interface in `src/models/base_model.py`; new model types extend it rather than adding parallel code paths.
- Keep hyperparameters in config, not code.

## Evaluation

- Always compare against a baseline (current production model and a naive baseline).
- Use metrics appropriate to the problem (e.g. PR-AUC for imbalanced classification, MAE/RMSE plus residual analysis for regression), and report per-segment performance, not only the aggregate.
- Define promotion thresholds explicitly in config and enforce them in the pipeline.

## Packaging and serving

- Register models with signatures; serving code loads by registry name/alias.
- Inference code validates input against the signature and returns explicit errors.
- Container images for training/serving are reproducible, pinned and non-root.

## Monitoring

- Drift detection (`src/monitoring/`) compares production inputs/predictions against the training reference stored with the model version.
- Export monitoring metrics with stable, low-cardinality Prometheus labels (model name, version, env), never per-request IDs.

## Testing ML code

- Unit test transformations and validators with small fixtures.
- Add a fast "train on tiny data" smoke test to catch pipeline breakage.
- Test the inference path end-to-end with a saved tiny model.
