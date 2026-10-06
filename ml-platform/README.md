# ML platform

Python components for training, inference, feature management, data validation and model monitoring.
Requires Python 3.10–3.12.

## Local setup

Run from this directory:

```bash
python -m pip install -e '.[dev]'
python -m src.cli create-sample data/sample.csv --n-samples 1000
python -m pytest tests/ -v
flake8 src/ tests/
black --check src/ tests/
```

See [the ML platform guide](../docs/ml-platform-guide.md) for configuration and pipeline usage.
Infrastructure and cluster deployment are managed from the repository root.
