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

{{- define "cfi-fed.agentrxUrl" -}}
{{- if and .Values.ingress.enabled .Values.replayHooks.enabled -}}
{{- printf "%s/agentrx/v1/replay" (include "cfi-fed.ingressBase" .) -}}
{{- else if .Values.client.agentrxUrl -}}
{{- .Values.client.agentrxUrl -}}
{{- else if .Values.replayHooks.enabled -}}
{{- printf "http://cfi-agentrx:%d/v1/replay" (int .Values.replayHooks.agentrx.port) -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end }}

{{- define "cfi-fed.causalflowUrl" -}}
{{- if and .Values.ingress.enabled .Values.replayHooks.enabled -}}
{{- printf "%s/causalflow/v1/counterfactual" (include "cfi-fed.ingressBase" .) -}}
{{- else if .Values.client.causalflowUrl -}}
{{- .Values.client.causalflowUrl -}}
{{- else if .Values.replayHooks.enabled -}}
{{- printf "http://cfi-causalflow:%d/v1/counterfactual" (int .Values.replayHooks.causalflow.port) -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end }}

{{- define "cfi-fed.replayMockUrl" -}}
{{- if and .Values.ingress.enabled .Values.replayHooks.enabled -}}
{{- printf "%s/replay/replay" (include "cfi-fed.ingressBase" .) -}}
{{- else if .Values.client.replayMockUrl -}}
{{- .Values.client.replayMockUrl -}}
{{- else if .Values.replayHooks.enabled -}}
{{- printf "http://cfi-replay-mock:%d/replay" (int .Values.replayHooks.mock.port) -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end }}

{{- define "cfi-fed.tauBenchUrl" -}}
{{- if and .Values.ingress.enabled .Values.replayHooks.enabled -}}
{{- printf "%s/tau/v1/tasks" (include "cfi-fed.ingressBase" .) -}}
{{- else if .Values.client.tauBenchUrl -}}
{{- .Values.client.tauBenchUrl -}}
{{- else if .Values.replayHooks.enabled -}}
{{- printf "http://cfi-tau:%d/v1/tasks" (int .Values.replayHooks.tau.port) -}}
{{- else -}}
{{- "" -}}
{{- end -}}
{{- end }}
