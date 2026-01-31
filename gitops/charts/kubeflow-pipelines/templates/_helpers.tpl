{{/*
Expand the name of the chart.
*/}}
{{- define "kubeflow-pipelines.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "kubeflow-pipelines.fullname" -}}
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
{{- define "kubeflow-pipelines.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "kubeflow-pipelines.labels" -}}
helm.sh/chart: {{ include "kubeflow-pipelines.chart" . }}
{{ include "kubeflow-pipelines.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "kubeflow-pipelines.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kubeflow-pipelines.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "kubeflow-pipelines.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "kubeflow-pipelines.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the MySQL hostname
*/}}
{{- define "kubeflow-pipelines.databaseHost" -}}
{{- if .Values.mysql.enabled }}
{{- printf "%s-mysql" (include "kubeflow-pipelines.fullname" .) }}
{{- else }}
{{- .Values.externalMysql.host }}
{{- end }}
{{- end }}

{{/*
Return the MySQL port
*/}}
{{- define "kubeflow-pipelines.databasePort" -}}
{{- if .Values.mysql.enabled }}
{{- printf "3306" }}
{{- else }}
{{- .Values.externalMysql.port | toString }}
{{- end }}
{{- end }}

{{/*
Return the MinIO/S3 endpoint
*/}}
{{- define "kubeflow-pipelines.s3Endpoint" -}}
{{- if .Values.minio.enabled }}
{{- printf "%s-minio:9000" (include "kubeflow-pipelines.fullname" .) }}
{{- else }}
{{- .Values.externalS3.endpoint }}
{{- end }}
{{- end }}

{{/*
Return the image registry prefix
*/}}
{{- define "kubeflow-pipelines.imageRegistry" -}}
{{- if .Values.global.imageRegistry }}
{{- printf "%s/" .Values.global.imageRegistry }}
{{- else }}
{{- printf "" }}
{{- end }}
{{- end }}
