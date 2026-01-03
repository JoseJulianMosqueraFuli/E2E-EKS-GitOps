# 🚀 Quick Start Guide

Guía rápida para empezar a usar la plataforma MLOps en menos de 10 minutos.

## 📋 Prerrequisitos

```bash
# Herramientas requeridas
- Python 3.8+
- Docker
- kubectl
- helm
- terraform
- aws-cli
```

## ⚡ Setup Rápido (5 minutos)

### 1. Clonar y Setup Inicial

```bash
# Clonar repositorio
git clone https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps.git
cd E2E-EKS-GitOps

# Setup del proyecto ML
cd ml-platform
python src/main.py setup --environment dev

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Entrenar tu Primer Modelo

```bash
# Crear datos de ejemplo
python src/main.py create-sample data/sample_data.csv \
    --n-samples 1000 --n-features 10 --task-type classification

# Entrenar modelo
python src/main.py train data/sample_data.csv

# ✅ Resultado: Modelo entrenado con MLflow tracking
```

### 3. Hacer Predicciones

```bash
# Crear datos para inferencia (sin target)
python -c "
import pandas as pd
data = pd.read_csv('data/sample_data.csv')
data.drop('target', axis=1).head(100).to_csv('data/inference_data.csv', index=False)
"

# Ejecutar inferencia
python src/main.py inference data/inference_data.csv \
    --model-path artifacts/model_*.joblib \
    --feature-pipeline-path artifacts/feature_pipeline_*.joblib \
    --output-path predictions.json \
    --return-probabilities

# ✅ Resultado: Predicciones guardadas en predictions.json
```

## 🏗️ Deploy Infraestructura (Opcional)

### Setup Rápido para Desarrollo

```bash
# Volver al directorio raíz
cd ..

# Deploy infraestructura dev
make quickstart-dev

# Deploy stack MLOps básico
make mlops-core

# ✅ Resultado: EKS + MLflow + Monitoring desplegados
```

### Acceder a Servicios

```bash
# MLflow UI
make port-forward-mlflow
# Abrir http://localhost:5000

# Grafana Dashboard
make port-forward-grafana
# Abrir http://localhost:3000 (admin/admin123)
```

## 🎯 Casos de Uso Rápidos

### Caso 1: Clasificación Binaria

```python
# train_classifier.py
from ml_platform.src.pipelines.training_pipeline import TrainingPipeline
from ml_platform.src.data.data_loader import DataLoader

# Crear datos
loader = DataLoader()
data = loader.create_sample_data(1000, 15, "classification")
data.to_csv("fraud_data.csv", index=False)

# Configuración
config = {
    'model': {
        'type': 'classification',
        'algorithm': 'random_forest',
        'hyperparameters': {'n_estimators': 100, 'max_depth': 10}
    },
    'preprocessing': {
        'feature_selection': {'enabled': True, 'k': 10}
    }
}

# Entrenar
pipeline = TrainingPipeline()
pipeline.config = config
results = pipeline.run_pipeline("fraud_data.csv")

print(f"Accuracy: {results['test_metrics']['accuracy']:.3f}")
```

### Caso 2: Regresión con Cross-Validation

```python
# train_regressor.py
from ml_platform.src.models.regression_model import RegressionModel
from ml_platform.src.data.data_loader import DataLoader

# Datos
loader = DataLoader()
data = loader.create_sample_data(1000, 20, "regression")

# Modelo
model = RegressionModel(
    model_name="price_predictor",
    algorithm="random_forest"
)

X = data.drop('target', axis=1)
y = data['target']

# Cross-validation
cv_results = model.cross_validate(X, y, cv=5, n_estimators=50)
print(f"CV R²: {cv_results['cv_r2_mean']:.3f} ± {cv_results['cv_r2_std']:.3f}")

# Entrenar modelo final
X_train, X_test, y_train, y_test = model.prepare_data(data, 'target')
metrics = model.train(X_train, y_train, X_test, y_test, n_estimators=100)
print(f"Test R²: {metrics['r2_score']:.3f}")
```

### Caso 3: Validación de Datos

```python
# validate_data.py
from ml_platform.src.data.data_validator import DataValidator
from ml_platform.src.data.data_loader import DataLoader

# Cargar datos
loader = DataLoader()
data = loader.load_csv("production_data.csv")

# Validar
validator = DataValidator()

# Crear suite basada en datos históricos
suite_name = validator.create_expectation_suite(
    "production_data_quality",
    data.sample(1000),  # Usar muestra para profiling
    overwrite=True
)

# Validar datos completos
results = validator.validate_data(data, suite_name)

if results['success']:
    print("✅ Data validation passed!")
else:
    print(f"❌ Data validation failed: {results['success_percent']:.1f}%")
    print(f"Report: {validator.get_validation_report_url()}")
```

### Caso 4: Inferencia por Lotes

```python
# batch_inference.py
from ml_platform.src.pipelines.inference_pipeline import InferencePipeline

# Cargar pipeline de inferencia
pipeline = InferencePipeline(
    model_path="artifacts/model_12345.joblib",
    feature_pipeline_path="artifacts/feature_pipeline_12345.joblib"
)

# Health check
health = pipeline.health_check()
print(f"Pipeline status: {health['status']}")

# Inferencia por lotes
results = pipeline.predict_batch(
    data_path="large_dataset.csv",
    output_path="batch_predictions.csv",
    batch_size=5000,
    return_probabilities=True
)

print(f"Processed {results['num_samples']} samples")
print(f"Avg time: {results['avg_inference_time_per_sample']:.4f}s per sample")

# Estadísticas
stats = pipeline.get_inference_stats()
print(f"Total predictions: {stats['total_predictions']}")
print(f"Error rate: {stats['error_rate']:.2%}")
```

## 🔧 Configuración Personalizada

### Archivo de Configuración

```yaml
# config/my_config.yaml
data:
  source: "s3"
  s3_bucket: "my-ml-data"
  target_column: "label"
  test_size: 0.15

model:
  type: "classification"
  algorithm: "xgboost"
  hyperparameters:
    n_estimators: 200
    max_depth: 8
    learning_rate: 0.1

preprocessing:
  numeric_strategy: "robust"
  feature_selection:
    enabled: true
    method: "rfe"
    k: 15

mlflow:
  experiment_name: "production_models"
  tracking_uri: "http://mlflow-server:5000"
```

### Usar Configuración Personalizada

```bash
# Entrenar con configuración personalizada
python src/main.py train data/my_data.csv \
    --config-name my_config \
    --environment prod
```

## 📊 Monitoreo y Debugging

### Logs Estructurados

```python
from ml_platform.src.utils.logging_config import setup_logging, MLOpsLogger

# Setup logging
setup_logging("config/logging.yaml")
logger = MLOpsLogger("my_pipeline")

# Log operaciones
logger.log_data_operation("load_data", {"rows": 1000, "source": "s3"})
logger.log_model_operation("train", "rf_classifier", {"accuracy": 0.95})
logger.log_metric("precision", 0.92, {"model": "rf", "dataset": "test"})
```

### Debugging Common Issues

```bash
# Verificar configuración
python -c "
from ml_platform.src.utils.config_manager import ConfigManager
cm = ConfigManager()
config = cm.load_config()
print(cm.get_config_summary(config))
"

# Test de conectividad MLflow
python -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
print('MLflow experiments:', mlflow.list_experiments())
"

# Verificar datos
python src/main.py validate data/my_data.csv --create-suite
```

## 🚀 Próximos Pasos

### Para Desarrollo Local

1. ✅ Completar quick start
2. 📖 Leer [ML Platform Guide](ml-platform-guide.md)
3. 🧪 Ejecutar tests: `pytest src/tests/ -v`
4. 🔧 Personalizar configuración
5. 📊 Explorar MLflow UI

### Para Producción

1. 🏗️ Deploy infraestructura: `make apply ENV=prod`
2. 🔒 Configurar secrets y IRSA
3. 📈 Setup monitoring: `make mlops-full`
4. 🔄 Configurar CI/CD pipelines
5. 📋 Implementar governance

### Recursos Adicionales

- 📚 [Documentación completa](ml-platform-guide.md)
- 🏢 [Recomendaciones Enterprise](mlops-enterprise-recommendations.md)
- 🔧 [Troubleshooting Guide](troubleshooting.md)
- 💬 [Community Discussions](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/discussions)

---

¡Felicidades! 🎉 Ya tienes una plataforma MLOps completa funcionando.

**¿Necesitas ayuda?** Abre un issue en GitHub o consulta la documentación detallada.
