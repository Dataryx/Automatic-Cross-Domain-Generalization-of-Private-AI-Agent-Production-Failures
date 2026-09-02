{{- define "cfi-fed.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "cfi-fed.fullname" -}}
{{- printf "%s" (include "cfi-fed.name" .) }}
{{- end }}

{{- define "cfi-fed.labels" -}}
app.kubernetes.io/name: {{ include "cfi-fed.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}
