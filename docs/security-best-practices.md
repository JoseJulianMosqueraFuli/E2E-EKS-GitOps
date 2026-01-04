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

## 🔑 Encryption

### At Rest

- S3: SSE-KMS encryption
- EBS: KMS encryption
- Secrets Manager: KMS encryption

### In Transit

- TLS 1.2+ para todas las comunicaciones
- mTLS con Istio service mesh

## 📋 Checklist de Seguridad

- [ ] Secrets en AWS Secrets Manager (no hardcodeados)
- [ ] IRSA configurado para cada service account
- [ ] Network policies aplicadas
- [ ] VPC endpoints habilitados
- [ ] KMS encryption para datos en reposo
- [ ] TLS habilitado para comunicaciones
- [ ] Container image scanning habilitado
- [ ] Pod Security Standards enforced

## 🚨 Respuesta a Incidentes

1. **Rotación de Secrets**: Actualizar en AWS Secrets Manager, ESO sincroniza automáticamente
2. **Revocación de Acceso**: Modificar IAM policies o eliminar role bindings
3. **Auditoría**: CloudTrail logs para todas las operaciones AWS

## 📚 Referencias

- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [EKS Security Best Practices](https://aws.github.io/aws-eks-best-practices/security/docs/)
- [IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
