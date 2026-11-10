# Flujos básicos de la plataforma

[Índice de documentación](../README.md) · [Arquitectura](implementation.md) · [Estado actual](../project/backlog.md)

Estos diagramas describen el código y los manifiestos del repositorio. La validación del despliegue
completo en AWS sigue pendiente; el backlog recoge la evidencia y los bloqueos.

## Arquitectura y responsabilidades

```mermaid
flowchart TB
    TF[Terraform] --> AWS[VPC, EKS, IAM, almacenamiento y ECR]
    Git[Repositorio Git] --> Flux[Flux]
    Git --> ArgoCD[ArgoCD]
    AWS --> EKS[Clúster EKS]
    EKS --> Flux
    Flux --> Infra[Controladores, add-ons y red]
    Flux --> ArgoCD
    ArgoCD --> Apps[Aplicaciones de la plataforma]
    Apps --> Argo[Argo Workflows]
    Apps --> MLflow[MLflow]
    Apps --> KServe[KServe y model-serving]
    Apps --> Monitoring[Monitoreo]
```

Terraform administra los recursos AWS; Flux, la infraestructura del clúster; ArgoCD, las aplicaciones.
Las flechas representan aprovisionamiento y reconciliación, no tráfico de red.

Fuente: [organización del repositorio](../../AGENTS.md#repository-layout).

## Entrenamiento y aprobación

```mermaid
flowchart TD
    Data[Dataset] --> Validate[Validar datos]
    Validate --> Split[Separar train, validación y test]
    Split --> Train[Entrenar preprocesamiento y modelo]
    Train --> Track[Guardar modelo y métricas en MLflow]
    Track --> Evaluate[Evaluar en test y comparar con champion]
    Evaluate --> Gate{¿Cumple los criterios?}
    Gate -->|No| Stop[No promover ni desplegar]
    Gate -->|Sí| Register[Registrar versión y guardar versión anterior]
    Register --> Alias[Asignar alias champion al candidato]
    Alias --> Deploy[Ejecutar workflow de despliegue]
```

Argo ejecuta los pasos con la imagen compartida `mlops-platform`. El preprocesamiento viaja
con el modelo en un `Pipeline` de scikit-learn. Si aún no existe un champion, la evaluación
aplica los umbrales del candidato sin comparación con una versión anterior.

Fuentes: [pipeline principal](../../gitops/applications/apps/argo-workflows/base/workflow-templates/ml-pipeline-template.yaml),
[entrenamiento](../../gitops/applications/apps/argo-workflows/base/workflow-templates/model-training-template.yaml)
y [pasos Python](../../ml-platform/src/pipelines/steps.py).

## Despliegue y rollback del modelo

```mermaid
flowchart TD
    Git[Git declara el InferenceService] --> ArgoCD[ArgoCD reconcilia model-serving]
    ArgoCD --> IS[InferenceService existente]
    Candidate[Candidato aprobado con alias champion] --> Rollout[Actualizar anotación de versión]
    IS --> Rollout
    Rollout --> Load[KServe renueva pods y carga champion]
    Load --> Verify{¿Versión y predicciones correctas?}
    Verify -->|Sí| Success[Despliegue verificado]
    Verify -->|No| Restore[Restaurar alias anterior o eliminarlo si no existía]
    Rollout -->|Error| Restore
    Restore --> Previous{¿Había versión anterior?}
    Previous -->|Sí| Rollback[Renovar pods con la versión anterior]
    Rollback --> Check[Verificar rollback]
    Check --> Failed[Workflow fallido: candidato rechazado]
    Previous -->|No| Failed
```

KServe usa el modo `Standard` y una actualización gradual de pods (`RollingUpdate`).
El alias decide qué modelo cargar; la anotación dispara la renovación. Un rollback también
se verifica y no convierte el despliegue fallido en un éxito. Si falla la restauración,
el workflow permanece fallido.

Fuentes: [workflow de despliegue](../../gitops/applications/apps/argo-workflows/base/workflow-templates/model-deployment-template.yaml)
y [InferenceService](../../gitops/applications/apps/model-serving/base/inference-service.yaml).

## Carga del modelo e inferencia

```mermaid
sequenceDiagram
    participant K as KServe
    participant S as Servidor step serve
    participant M as MLflow Registry
    participant A as Almacén de artefactos
    participant C as Cliente autorizado
    K->>S: Iniciar pod
    S->>M: Resolver alias champion
    M-->>S: Versión registrada
    S->>M: Solicitar modelo de esa versión
    M-->>S: Información de descarga
    S->>A: Descargar artefactos
    A-->>S: Pipeline de preprocesamiento y modelo
    S->>S: Cargar modelo en memoria
    C->>S: POST /invocations con datos
    S->>S: Preprocesar y predecir
    S-->>C: Predicciones y X-Model-Version
```

El alias se resuelve al arrancar, no en cada petición. El acceso al almacén depende del entorno
y de la configuración de MLflow: gateway compatible con S3 en desarrollo, S3 en producción.
El diagrama resume la carga; omite los saltos internos del proxy de artefactos.
El cliente debe tener conectividad y permisos de red; aquí no se presupone un endpoint público.

Fuente: [servidor de inferencia](../../ml-platform/src/pipelines/serving.py).

## CI, publicación y promoción de entornos

```mermaid
flowchart TD
    Change[Push o pull request] --> CI[GitHub Actions: validaciones y pruebas]
    CI --> Images[Construir y escanear imágenes]
    Publish[Workflow de publicación ECR por OIDC] --> Build[Construir las tres imágenes]
    Build --> Scan{¿Pasan los controles Trivy?}
    Scan -->|No| Block[Bloquear publicación]
    Scan -->|Sí| ECR[Publicar en ECR]
    Dev[Rama develop: dev] --> ValidateStage[Validar origen y destino]
    ValidateStage --> PRStage[PR hacia staging]
    PRStage --> MergeStage[Revisar y fusionar]
    MergeStage --> Stage[Rama staging]
    Stage --> ValidateProd[Validar origen y destino]
    ValidateProd --> PRProd[PR hacia main]
    PRProd --> MergeProd[Revisar y fusionar]
    MergeProd --> Prod[Rama main: producción]
    Stage --> Sync[Flux y ArgoCD reconcilian desde Git]
    Prod --> Sync
```

Publicar imágenes y promover configuración son flujos distintos. El workflow de promoción
crea o reutiliza un PR entre ramas; no aplica recursos al clúster directamente.
La promoción del mismo digest ECR entre entornos sigue pendiente en el backlog (#65).

Fuentes: [CI](../../.github/workflows/ci.yml), [imágenes](../../.github/workflows/ml-platform-image.yml),
[publicación ECR](../../.github/workflows/publish-ecr.yml) y
[promoción](../../.github/workflows/environment-promotion.yml).
