# ML Inference Application

This directory contains the ML inference service code and configurations.

## Structure

- `src/` - Inference service source code
- `tests/` - Unit and integration tests
- `config/` - Service configuration files
- `Dockerfile` - Container image definition

## Usage

1. Install dependencies: `pip install -r requirements.txt`
2. Run service: `python src/serve.py`
3. Build container: `docker build -t inference .`