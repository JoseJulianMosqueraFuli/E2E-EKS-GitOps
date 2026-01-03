# 🤖 ML Platform Guide

Guía completa para usar la plataforma ML implementada en el proyecto MLOps Enterprise.

## 📋 Tabla de Contenidos

- [Arquitectura del Código ML](#arquitectura-del-código-ml)
- [Modelos Disponibles](#modelos-disponibles)
- [Pipelines de Entrenamiento](#pipelines-de-entrenamiento)
- [Pipelines de Inferencia](#pipelines-de-inferencia)
- [Validación de Datos](#validación-de-datos)
- [Feature Engineering](#feature-engineering)
- [Configuración](#configuración)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [CLI Commands](#cli-commands)
- [Testing](#testing)

## 🏗️ Arquitectura del Código ML

```
ml-platform/src/
├── 🤖 models/                    # Modelos ML con MLflow
│   ├── base_model.py            # Clase base abstracta
│   ├── classification_model.py  # Modelos de clasificación
│   └── regression_model.py      # Modelos de regresión
├── 📊 data/                     # Procesamiento de datos
│   ├── data_loader.py           # Carga desde S3/local
│   ├── data_validator.py        # Great Expectations
│   └── feature_engineering.py  # Transformaciones
├── 🔄 pipelines/                # Pipelines end-to-end
│   ├── training_pipeline.py    # Pipeline de entrenamiento
│   └── inference_pipeline.py   # Pipeline de inferencia
├── 🛠️ utils/                    # Utilidades
│   ├── logging_config.py        # Configuración de logs
│   └── config_manager.py        # Gestión de configuración
├── 🧪 tests/                    # Tests unitarios
└── main.py                      # CLI principal
```

## 🤖 Modelos Disponibles

### Modelos de Clasificación

**Algoritmos soportados:**

- `random_forest` - Random Forest Classifier
- `xgboost` - XGBoost Classifier (si está instalado)
- `logistic_regression` - Logistic Regression

**Ejemplo de uso:**

```python
from ml_platform.src.models.classification_model import ClassificationModel

# Inicializar modelo
model = ClassificationModel(
    model_name="fraud_detector",
    algorithm="random_forest",
    experiment_name="fraud_detection"
)

# Entrenar
metrics = model.train(X_train, y_train, X_test, y_test,
                     n_estimators=100, max_depth=10)

# Predicciones con confianza
results = model.predict_with_confidence(X_new, confidence_threshold=0.8)
```

### Modelos de Regresión

**Algoritmos soportados:**

- `random_forest` - Random Forest Regressor
- `xgboost` - XGBoost Regressor (si está instalado)
- `linear_regression` - Linear Regression
- `ridge` - Ridge Regression
- `lasso` - Lasso Regression

**Ejemplo de uso:**

```python
from ml_platform.src.models.regression_model import RegressionModel

# Inicializar modelo
model = RegressionModel(
    model_name="price_predictor",
    algorithm="random_forest",
    experiment_name="price_prediction"
)

# Entrenar con cross-validation
cv_results = model.cross_validate(X, y, cv=5)

# Predicciones con intervalos
results = model.predict_with_intervals(X_new, confidence_level=0.95)
```

## 🔄 Pipelines de Entrenamiento

### Pipeline Completo

El `TrainingPipeline` ejecuta todo el flujo de entrenamiento:

1. **Carga de datos** (local/S3)
2. **Validación de calidad** (Great Expectations)
3. **Feature engineering** (scaling, encoding, selection)
4. **División de datos** (train/val/test)
5. **Entrenamiento** con MLflow tracking
6. **Evaluación** en conjunto de test
7. **Guardado de artefactos**

**Ejemplo de uso:**

```python
from ml_platform.src.pipelines.training_pipeline import TrainingPipeline

# Configuración
config = {
    'data': {
        'source': 'local',
        'format': 'csv',
        'target_column': 'target'
    },
    'model': {
        'type': 'classification',
        'algorithm': 'random_forest',
        'hyperparameters': {
            'n_estimators': 100,
            'max_depth': 10
        }
    }
}

# Ejecutar pipeline
pipeline = TrainingPipeline()
pipeline.config = config
results = pipeline.run_pipeline("data/training_data.csv")

print(f"Run ID: {results['run_id']}")
print(f"Test Accuracy: {results['test_metrics']['accuracy']:.3f}")
```

### Configuración del Pipeline

```yaml
# config/training_config.yaml
data:
  source: "s3" # local, s3
  format: "csv" # csv, parquet, json
  target_column: "target"
  test_size: 0.2
  validation_size: 0.1
  s3_bucket: "mlops-dev-data"

model:
  type: "classification" # classification, regression
  algorithm: "random_forest"
  hyperparameters:
    n_estimators: 100
    max_depth: 10
    random_state: 42

preprocessing:
  numeric_strategy: "standard" # standard, minmax, robust
  categorical_strategy: "onehot" # onehot, ordinal, label
  feature_selection:
    enabled: true
    method: "k_best" # k_best, percentile, rfe, rfecv
    k: 10

validation:
  enabled: true
  create_suite: true
  fail_on_validation_error: false

mlflow:
  experiment_name: "production_models"
  tracking_uri: "http://mlflow-server:5000"
```

## 🚀 Pipelines de Inferencia

### Inferencia Individual y por Lotes

**Ejemplo de inferencia individual:**

```python
from ml_platform.src.pipelines.inference_pipeline import InferencePipeline

# Cargar modelo entrenado
pipeline = InferencePipeline(
    model_path="artifacts/model_12345.joblib",
    feature_pipeline_path="artifacts/feature_pipeline_12345.joblib"
)

# Predicción individual
results = pipeline.predict(
    new_data,
    return_probabilities=True,
    confidence_threshold=0.8
)

print(f"Predictions: {results['predictions']}")
print(f"Confident: {results['confident_count']}/{results['num_samples']}")
```

**Ejemplo de inferencia por lotes:**

```python
# Inferencia por lotes desde archivo
batch_results = pipeline.predict_batch(
    data_path="data/inference_data.csv",
    output_path="data/predictions.csv",
    batch_size=1000,
    return_probabilities=True
)

print(f"Processed {batch_results['num_samples']} samples")
print(f"Avg time: {batch_results['avg_inference_time_per_sample']:.4f}s")
```

### Health Check y Monitoreo

```python
# Verificar estado del pipeline
health = pipeline.health_check()
print(f"Status: {health['status']}")

# Estadísticas de inferencia
stats = pipeline.get_inference_stats()
print(f"Total predictions: {stats['total_predictions']}")
print(f"Error rate: {stats['error_rate']:.2%}")
```

## 📊 Validación de Datos

### Great Expectations Integration

**Validación automática:**

```python
from ml_platform.src.data.data_validator import DataValidator

# Inicializar validador
validator = DataValidator()

# Crear suite de expectativas basada en datos
suite_name = validator.create_expectation_suite(
    "data_quality_suite",
    sample_data,
    overwrite=True
)

# Validar datos nuevos
results = validator.validate_data(new_data, suite_name)

print(f"Validation success: {results['success']}")
print(f"Success rate: {results['success_percent']:.1f}%")
```

**Expectativas incluidas automáticamente:**

- ✅ Conteo de filas válido
- ✅ Columnas esperadas presentes
- ✅ Tipos de datos correctos
- ✅ Valores no nulos (según distribución)
- ✅ Rangos numéricos válidos
- ✅ Longitudes de strings válidas
- ✅ Rangos de fechas válidos

## 🔧 Feature Engineering

### Preprocessing Pipeline

**Transformaciones automáticas:**

```python
from ml_platform.src.data.feature_engineering import FeatureEngineer

fe = FeatureEngineer()

# Configurar preprocessor
fe.create_preprocessor(
    numeric_features=['age', 'income', 'score'],
    categorical_features=['category', 'region'],
    numeric_strategy='standard',      # standard, minmax, robust
    categorical_strategy='onehot'     # onehot, ordinal, label
)

# Entrenar y transformar
X_transformed = fe.fit_transform(X_train)

# Transformar datos nuevos
X_test_transformed = fe.transform(X_test)
```

### Feature Selection

**Métodos disponibles:**

- `k_best` - SelectKBest con F-score
- `percentile` - SelectPercentile
- `mutual_info` - Mutual Information
- `rfe` - Recursive Feature Elimination
- `rfecv` - RFE with Cross-Validation

```python
# Selección de features
X_selected = fe.select_features(
    X_transformed, y,
    method='k_best',
    k=10,
    task_type='classification'
)

# Obtener nombres de features seleccionadas
selected_names = fe.get_selected_feature_names()
```

### Transformadores Personalizados

```python
from ml_platform.src.data.feature_engineering import CustomTransformers

# Extractor de features de fecha
date_extractor = CustomTransformers.DateTimeFeatureExtractor(['created_at'])

# Clipper de outliers
outlier_clipper = CustomTransformers.OutlierClipper(['price', 'quantity'])

# Features polinomiales
poly_features = CustomTransformers.PolynomialFeatures(['feature_1'], degree=2)
```

## ⚙️ Configuración

### ConfigManager

**Gestión centralizada de configuración:**

```python
from ml_platform.src.utils.config_manager import ConfigManager

# Inicializar para ambiente dev
config_manager = ConfigManager(environment="dev")

# Cargar configuración
config = config_manager.load_config()

# Validar configuración
is_valid = config_manager.validate_config(config)

# Resumen de configuración
summary = config_manager.get_config_summary(config)
```

### Configuración por Ambiente

```
config/
├── config.yaml              # Configuración base
├── config.dev.yaml          # Overrides para dev
├── config.staging.yaml      # Overrides para staging
├── config.prod.yaml         # Overrides para prod
└── secrets.example.yaml     # Ejemplo de secrets
```

### Variables de Entorno

```bash
# Configuración MLflow
export MLFLOW_TRACKING_URI="http://mlflow-server:5000"
export MLFLOW_REGISTRY_URI="http://mlflow-server:5000"

# Configuración AWS
export AWS_REGION="us-west-2"
export S3_BUCKET="mlops-dev-data"

# Ambiente
export MLOPS_ENV="dev"
```

## 🖥️ CLI Commands

### Setup del Proyecto

```bash
# Configurar estructura del proyecto
python src/main.py setup --environment dev

# Crear datos de ejemplo
python src/main.py create-sample data/sample.csv \
    --n-samples 1000 --n-features 10 --task-type classification
```

### Entrenamiento

```bash
# Entrenar modelo con configuración por defecto
python src/main.py train data/training_data.csv

# Entrenar con configuración específica
python src/main.py train data/training_data.csv \
    --config-name custom_config --environment prod
```

### Inferencia

```bash
# Inferencia individual
python src/main.py inference data/new_data.csv \
    --model-path artifacts/model_12345.joblib \
    --feature-pipeline-path artifacts/feature_pipeline_12345.joblib \
    --output-path predictions.json

# Inferencia por lotes
python src/main.py inference data/batch_data.csv \
    --model-uri "models:/fraud_detector/Production" \
    --batch-inference --batch-size 5000 \
    --output-path batch_predictions.csv
```

### Validación de Datos

```bash
# Validar datos con suite existente
python src/main.py validate data/new_data.csv \
    --suite-name production_data_suite

# Crear nueva suite y validar
python src/main.py validate data/new_data.csv \
    --create-suite --suite-name new_data_suite
```

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
cd ml-platform
python -m pytest src/tests/ -v

# Tests específicos
python -m pytest src/tests/test_models.py -v
python -m pytest src/tests/test_data.py -v

# Tests con coverage
python -m pytest src/tests/ --cov=src --cov-report=html
```

### Tests Incluidos

**test_models.py:**

- ✅ Inicialización de modelos
- ✅ Entrenamiento y métricas
- ✅ Predicciones y probabilidades
- ✅ Feature importance
- ✅ Predicciones con confianza
- ✅ Intervalos de predicción
- ✅ Cross-validation

**test_data.py:**

- ✅ Carga de datos (CSV, Parquet, JSON)
- ✅ Guardado de datos
- ✅ Creación de datos de ejemplo
- ✅ Feature engineering pipeline
- ✅ Selección de features
- ✅ Guardado/carga de pipelines

## 📈 Ejemplos Completos

### Ejemplo 1: Clasificación End-to-End

```python
# 1. Crear datos de ejemplo
from ml_platform.src.data.data_loader import DataLoader

loader = DataLoader()
data = loader.create_sample_data(1000, 10, "classification")
data.to_csv("data/classification_data.csv", index=False)

# 2. Entrenar modelo
from ml_platform.src.pipelines.training_pipeline import TrainingPipeline

pipeline = TrainingPipeline()
results = pipeline.run_pipeline("data/classification_data.csv")

# 3. Inferencia
from ml_platform.src.pipelines.inference_pipeline import InferencePipeline

inference = InferencePipeline(
    model_path=f"artifacts/model_{results['run_id']}.joblib",
    feature_pipeline_path=f"artifacts/feature_pipeline_{results['run_id']}.joblib"
)

# Datos nuevos (sin target)
new_data = data.drop('target', axis=1).head(10)
predictions = inference.predict(new_data, return_probabilities=True)

print(f"Predictions: {predictions['predictions']}")
```

### Ejemplo 2: Pipeline con Validación

```python
# 1. Validar datos antes del entrenamiento
from ml_platform.src.data.data_validator import DataValidator

validator = DataValidator()
suite_name = validator.create_expectation_suite("training_data", data)
validation_results = validator.validate_data(data, suite_name)

if not validation_results['success']:
    print(f"Data validation failed: {validation_results['success_percent']:.1f}%")
    # Decidir si continuar o no

# 2. Entrenar solo si la validación pasa
if validation_results['success_percent'] > 90:  # Umbral configurable
    pipeline = TrainingPipeline()
    results = pipeline.run_pipeline("data/classification_data.csv")
```

### Ejemplo 3: Monitoreo de Inferencia

```python
# Pipeline de inferencia con monitoreo
inference = InferencePipeline(model_path="model.joblib")

# Procesar múltiples lotes
for batch_file in ["batch1.csv", "batch2.csv", "batch3.csv"]:
    results = inference.predict_batch(batch_file, f"predictions_{batch_file}")

    # Verificar estadísticas
    stats = inference.get_inference_stats()
    if stats['error_rate'] > 0.05:  # 5% error threshold
        print(f"High error rate detected: {stats['error_rate']:.2%}")
        # Alertar o tomar acción

# Health check periódico
health = inference.health_check()
if health['status'] != 'healthy':
    print(f"Pipeline unhealthy: {health}")
```

## 🔗 Integración con MLOps Stack

### MLflow Integration

- **Automatic experiment tracking** durante entrenamiento
- **Model registry** para versionado de modelos
- **Artifact logging** para pipelines y modelos
- **Metrics logging** para todas las métricas de evaluación

### Kubernetes Deployment

Los modelos entrenados pueden ser desplegados usando:

- **KServe** para serving serverless
- **Seldon Core** para deployments complejos
- **Argo Workflows** para pipelines de entrenamiento

### Monitoring Integration

- **Prometheus metrics** para monitoreo de inferencia
- **Grafana dashboards** para visualización
- **Great Expectations** para calidad de datos
- **MLflow tracking** para drift detection

---

Esta guía cubre todos los aspectos del código ML implementado. Para más detalles sobre la infraestructura y deployment, consulta el [README principal](../README.md) y la [documentación de recomendaciones MLOps](mlops-enterprise-recommendations.md).
