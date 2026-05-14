# Model Monitoring con Evidently

Guía para detectar data drift y model drift automáticamente usando Evidently AI.

## Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Production     │────▶│  Evidently       │────▶│  Prometheus │
│  Data           │     │  Monitoring      │     │  + Grafana  │
└─────────────────┘     │  Service         │     └─────────────┘
                        └────────┬─────────┘            │
                                 │                      │
                        ┌────────▼─────────┐     ┌──────▼──────┐
                        │  CronJob         │     │  Alertas    │
                        │  (Drift Check)   │     │  (Slack)    │
                        └──────────────────┘     └─────────────┘
```

## Componentes

### 1. DriftDetector (`ml-platform/src/monitoring/drift_detector.py`)

Detecta data drift comparando datos de referencia con datos actuales.

```python
from monitoring import DriftDetector
import pandas as pd

# Cargar datos
reference_data = pd.read_csv("reference.csv")
current_data = pd.read_csv("current.csv")

# Detectar drift
detector = DriftDetector(reference_data)
results = detector.detect_data_drift(current_data)

print(f"Drift detectado: {results['dataset_drift']}")
print(f"Columnas con drift: {results['drifted_columns']}")
```

### 2. ModelMonitor (`ml-platform/src/monitoring/model_monitor.py`)

Monitoreo completo incluyendo performance del modelo.

```python
from monitoring import ModelMonitor

monitor = ModelMonitor(
    reference_data=reference_data,
    model_type="classification",
    target_column="target",
    prediction_column="prediction",
)

results = monitor.run_monitoring(current_data)
print(f"Health status: {results['health_status']}")
```

### 3. MetricsExporter (`ml-platform/src/monitoring/metrics_exporter.py`)

Exporta métricas a Prometheus.

```python
from monitoring import MetricsExporter

exporter = MetricsExporter(
    model_name="fraud-detection",
    model_version="1.0",
)

exporter.update_from_monitoring_results(results)
exporter.push_metrics("http://prometheus-pushgateway:9091")
```

## Despliegue en Kubernetes

### 1. Aplicar manifiestos

```bash
kubectl apply -k k8s/mlops-stack/monitoring/
```

### 2. Registrar un modelo

```bash
curl -X POST http://evidently-monitoring.ml-monitoring:8080/models/register \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "fraud-detection",
    "model_version": "1.0",
    "model_type": "classification",
    "target_column": "is_fraud",
    "prediction_column": "prediction",
    "reference_data_path": "/data/reference/fraud_reference.parquet"
  }'
```

### 3. Ejecutar monitoreo

```bash
curl -X POST http://evidently-monitoring.ml-monitoring:8080/monitoring/run \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "fraud-detection",
    "current_data_path": "/data/current/fraud_current.parquet",
    "include_performance": true,
    "generate_report": true
  }'
```

## Métricas Prometheus

| Métrica                              | Descripción                      |
| ------------------------------------ | -------------------------------- |
| `ml_data_drift_detected`             | 1 si se detectó drift, 0 si no   |
| `ml_data_drift_share`                | Porcentaje de features con drift |
| `ml_drifted_columns_count`           | Número de columnas con drift     |
| `ml_model_health_status`             | 0=healthy, 1=warning, 2=critical |
| `ml_model_accuracy`                  | Accuracy actual del modelo       |
| `ml_model_f1_score`                  | F1 score actual                  |
| `ml_performance_degradation_percent` | Degradación vs referencia        |

## Alertas

Las alertas se configuran en `prometheus-alerts.yaml`:

- **DataDriftDetected**: Cuando se detecta drift en cualquier modelo
- **HighDriftShare**: Cuando >30% de features tienen drift
- **ModelHealthCritical**: Cuando el modelo está en estado crítico
- **ModelPerformanceDegraded**: Cuando la performance baja >10%

## CronJob

El CronJob `drift-detection-job` ejecuta cada hora:

1. Carga datos actuales de producción
2. Ejecuta detección de drift para cada modelo registrado
3. Actualiza métricas en Prometheus
4. Envía alertas a Slack si hay drift crítico

## Configuración

Editar `drift-detection-config` ConfigMap para agregar modelos:

```yaml
models:
  - name: mi-modelo
    version: "1.0"
    type: classification
    reference_data: s3://bucket/reference.parquet
```

## Dashboard Grafana

Acceder al dashboard "ML Model Monitoring" en Grafana para visualizar:

- Estado de salud de todos los modelos
- Drift share por modelo
- Columnas con drift
- Tendencias de performance
