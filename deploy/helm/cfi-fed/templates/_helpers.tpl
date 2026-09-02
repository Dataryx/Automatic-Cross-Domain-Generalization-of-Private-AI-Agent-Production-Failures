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

{{- define "cfi-fed.ingressScheme" -}}
{{- if .Values.ingress.tls -}}https{{- else -}}http{{- end -}}
{{- end }}

{{- define "cfi-fed.ingressBase" -}}
{{- printf "%s://%s" (include "cfi-fed.ingressScheme" .) .Values.ingress.host -}}
{{- end }}

{{- define "cfi-fed.registryUrl" -}}
{{- if .Values.ingress.enabled -}}
{{- printf "%s/registry" (include "cfi-fed.ingressBase" .) -}}
{{- else -}}
{{- .Values.client.registryUrl -}}
{{- end -}}
{{- end }}

{{- define "cfi-fed.coordinatorUrl" -}}
{{- if .Values.ingress.enabled -}}
{{- printf "%s/coordinator" (include "cfi-fed.ingressBase" .) -}}
{{- else -}}
{{- .Values.client.coordinatorUrl -}}
{{- end -}}
{{- end }}

{{- define "cfi-fed.aggregatorUrl" -}}
{{- if .Values.ingress.enabled -}}
{{- printf "%s/aggregator" (include "cfi-fed.ingressBase" .) -}}
{{- else -}}
{{- .Values.client.aggregatorUrl -}}
{{- end -}}
{{- end }}
