# Security Best Practices for MLOps Platform

Esta guía documenta las mejores prácticas de seguridad implementadas en la plataforma MLOps.

## 🔐 Secrets Management

### External Secrets Operator (ESO)

Utilizamos ESO para sincronizar secrets desde AWS Secrets Manager:

```bash
# Crear secret en AWS
aws secretsmanager create-secret \
  --name mlops/grafana \
  --secret-string '{"admin-password":"YOUR_SECURE_PASSWORD"}'

# Aplicar External Secrets
kubectl apply -k k8s/mlops-stack/secrets/
```

**Nunca hardcodear credenciales** en archivos YAML o código fuente.

### Secrets Gestionados

| Componente     | Secret Name       | Ubicación AWS         |
| -------------- | ----------------- | --------------------- |
| Grafana        | grafana-secrets   | mlops/grafana         |
| MLflow         | mlflow-secrets    | mlops/mlflow/database |
| Argo Workflows | argo-artifacts-s3 | mlops/argo/s3         |
| KServe         | storage-config    | mlops/kserve/s3       |

## 🛡️ IAM Roles for Service Accounts (IRSA)

Cada componente tiene su propio IAM role con permisos mínimos:

```yaml
# Ejemplo: Service Account con IRSA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mlflow-sa
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/mlflow-s3-role
```

### Roles Configurados

| Service Account  | Namespace        | Permisos            |
| ---------------- | ---------------- | ------------------- |
| external-secrets | external-secrets | SecretsManager:Read |
| mlflow-sa        | mlflow           | S3:ReadWrite        |
| argo-workflow-s3 | argo-workflows   | S3:ReadWrite        |
| models-sa        | models           | S3:Read             |

## 🔒 Network Security

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
spec:
  podSelector: {}
  policyTypes:
    - Ingress
```

### VPC Endpoints

Configurados para acceso privado a servicios AWS:

- S3 Gateway Endpoint
- ECR API/DKR Interface Endpoints
- Secrets Manager Interface Endpoint

## 🛡️ Pod Security Standards

Todos los namespaces aplican **Pod Security Standards restricted**:

```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
```

### Security Contexts Requeridos

Cada contenedor debe incluir:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
  seccompProfile:
    type: RuntimeDefault
```

### ResourceQuotas y LimitRanges

Cada namespace tiene límites de recursos para prevenir DoS:

```yaml
# ResourceQuota
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
    pods: "10"
```

## 🔑 Encryption

### At Rest

- S3: SSE-KMS encryption
- EBS: KMS encryption
- Secrets Manager: KMS encryption

### In Transit

- TLS 1.2+ para todas las comunicaciones
- ACM certificates for ALB Ingress (MLflow, Grafana, etc.)
  ```bash
  # Request a certificate for your domain
  aws acm request-certificate \
    --domain-name mlflow.mlops.company.com \
    --validation-method DNS \
    --region us-west-2

  # Update the Helm values with the certificate ARN
  # gitops/charts/mlflow/values.yaml
  #   alb.ingress.kubernetes.io/certificate-arn: "arn:aws:acm:..."
  ```
- mTLS con Istio service mesh

## 📋 Checklist de Seguridad

- [x] Secrets en AWS Secrets Manager (no hardcodeados)
- [x] IRSA configurado para cada service account
- [x] Network policies aplicadas
- [x] VPC endpoints habilitados
- [x] KMS encryption para datos en reposo
- [x] TLS habilitado para comunicaciones
- [x] Container image scanning habilitado (ECR scan-on-push)
- [x] Pod Security Standards enforced (restricted)
- [x] seccompProfile: RuntimeDefault en todos los pods
- [x] ResourceQuotas y LimitRanges por namespace
- [x] automountServiceAccountToken: false por defecto
- [x] Pre-commit hooks con detect-secrets
- [x] Security Groups egress restringidos a VPC CIDR
- [x] EKS API endpoint público deshabilitado por defecto
- [x] S3 force_destroy eliminado (protección contra borrado)

## 🚨 Respuesta a Incidentes

1. **Rotación de Secrets**: Actualizar en AWS Secrets Manager, ESO sincroniza automáticamente
2. **Revocación de Acceso**: Modificar IAM policies o eliminar role bindings
3. **Auditoría**: CloudTrail logs para todas las operaciones AWS

## 📚 Referencias

- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [EKS Security Best Practices](https://aws.github.io/aws-eks-best-practices/security/docs/)
- [IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
