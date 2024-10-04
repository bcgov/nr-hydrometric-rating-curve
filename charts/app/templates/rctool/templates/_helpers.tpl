{{/*
Expand the name of the chart.
*/}}
{{- define "rctool.name" -}}
{{- printf "rctool" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "rctool.fullname" -}}
{{- $componentName := include "rctool.name" .  }}
{{- if .Values.rctool.fullnameOverride }}
{{- .Values.rctool.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $componentName | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "rctool.labels" -}}
{{ include "rctool.selectorLabels" . }}
{{- if .Values.global.tag }}
app.kubernetes.io/image-version: {{ .Values.global.tag | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/short-name: {{ include "rctool.name" . }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "rctool.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rctool.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}


