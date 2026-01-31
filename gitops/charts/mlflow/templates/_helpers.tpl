{{/*
Expand the name of the chart.
*/}}
{{- define "mlflow.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "mlflow.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mlflow.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mlflow.labels" -}}
helm.sh/chart: {{ include "mlflow.chart" . }}
{{ include "mlflow.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mlflow.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mlflow.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "mlflow.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mlflow.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL hostname
*/}}
{{- define "mlflow.databaseHost" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "mlflow.fullname" .) }}
{{- else }}
{{- .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL port
*/}}
{{- define "mlflow.databasePort" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "5432" }}
{{- else }}
{{- .Values.externalDatabase.port | toString }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL database name
*/}}
{{- define "mlflow.databaseName" -}}
{{- if .Values.postgresql.enabled }}
{{- .Values.postgresql.auth.database }}
{{- else }}
{{- .Values.externalDatabase.database }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL user
*/}}
{{- define "mlflow.databaseUser" -}}
{{- if .Values.postgresql.enabled }}
{{- .Values.postgresql.auth.username }}
{{- else }}
{{- .Values.externalDatabase.user }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL secret name
*/}}
{{- define "mlflow.databaseSecretName" -}}
{{- if .Values.postgresql.enabled }}
{{- if .Values.postgresql.auth.existingSecret }}
{{- .Values.postgresql.auth.existingSecret }}
{{- else }}
{{- printf "%s-postgresql" (include "mlflow.fullname" .) }}
{{- end }}
{{- else }}
{{- if .Values.externalDatabase.existingSecret }}
{{- .Values.externalDatabase.existingSecret }}
{{- else }}
{{- printf "%s-external-db" (include "mlflow.fullname" .) }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Return the PostgreSQL secret key
*/}}
{{- define "mlflow.databaseSecretKey" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "password" }}
{{- else }}
{{- .Values.externalDatabase.existingSecretPasswordKey | default "postgres-password" }}
{{- end }}
{{- end }}
