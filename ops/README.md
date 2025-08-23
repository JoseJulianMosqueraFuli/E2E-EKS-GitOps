# Operations

This directory contains operational tools, scripts, and configurations for monitoring and maintenance.

## Structure

- `monitoring/` - Prometheus, Grafana configurations
- `logging/` - Log aggregation and analysis tools
- `scripts/` - Operational automation scripts
- `docs/` - Runbooks and operational procedures

## Usage

1. Deploy monitoring: `kubectl apply -f monitoring/`
2. View dashboards: Access Grafana at configured endpoint
3. Run maintenance: `./scripts/maintenance.sh`