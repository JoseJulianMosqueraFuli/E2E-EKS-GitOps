# ML Training Application

This directory contains the ML training application code and configurations.

## Structure

- `src/` - Training application source code
- `tests/` - Unit and integration tests
- `config/` - Training configuration files
- `Dockerfile` - Container image definition

## Usage

1. Install dependencies: `pip install -r requirements.txt`
2. Run training: `python src/train.py`
3. Build container: `docker build -t trainer .`