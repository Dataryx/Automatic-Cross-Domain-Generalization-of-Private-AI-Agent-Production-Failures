# CFI-Fed developer commands

.PHONY: install test sim dod golden tau tau-live agent-hooks cross-boundary corpus-publish end-to-end federation full-pipeline compose-full-pipeline postgres-compose-full-pipeline tls-full-pipeline mtls-full-pipeline stack stack-postgres stack-tls stack-mtls health live-replay replay-profiles eval-harnesses compose-smoke postgres-smoke helm-chart remote-registry contribute-publish audit-attest mypy figures field-study ingest-corpus eval-all certs observability hardening auth release verify-release mtls console console-dev console-build

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -q

sim:
	python tools/feasibility/run_cfi_sim.py
	python scripts/ci/verify_sim.py

dod:
	python tools/evaluation/verify_dod.py

golden:
	python scripts/ops/golden_path.py

tau:
	python tools/evaluation/benchmarks/tau_adapter.py

tau-live:
	python scripts/ci/verify_tau_live.py

eval-all:
	python tools/evaluation/run_all.py

health:
	python scripts/ops/health_check.py

live-replay:
	python scripts/ops/live_replay_smoke.py

replay-profiles:
	python scripts/ci/verify_replay_profiles.py

eval-harnesses:
	python scripts/ci/verify_eval_harnesses.py

compose-smoke:
	python scripts/ci/verify_compose_stack.py

postgres-smoke:
	python scripts/ci/verify_postgres_compose.py

helm-chart:
	python scripts/ci/verify_helm_chart.py

remote-registry:
	python scripts/ci/verify_remote_registry_cli.py

contribute-publish:
	python scripts/ci/verify_contribute_publish.py

agent-hooks:
	python scripts/ci/verify_agent_hooks.py

cross-boundary:
	python scripts/ci/verify_cross_boundary.py

corpus-publish:
	python scripts/ci/verify_corpus_publish.py

end-to-end:
	python scripts/ci/verify_end_to_end.py

federation:
	python scripts/ci/verify_federation_workflow.py

full-pipeline:
	python scripts/ci/verify_full_pipeline.py

cli-endpoints:
	python scripts/ci/verify_cli_endpoints.py

pipeline-matrix:
	python scripts/ci/verify_pipeline_matrix.py

compose-full-pipeline:
	python scripts/ci/verify_compose_full_pipeline.py

postgres-compose-full-pipeline:
	python scripts/ci/verify_postgres_compose_full_pipeline.py

tls-full-pipeline:
	python scripts/ci/verify_tls_full_pipeline.py

mtls-full-pipeline:
	python scripts/ci/verify_mtls_full_pipeline.py

postgres-tls-full-pipeline:
	python scripts/ci/verify_postgres_tls_full_pipeline.py

mtls-required-full-pipeline:
	python scripts/ci/verify_mtls_required_full_pipeline.py

pipeline-matrix-ci:
	CFI_REQUIRE_DOCKER=1 python scripts/ci/verify_pipeline_matrix_ci.py

audit-attest:
	python scripts/ci/verify_audit_attestation.py

figures:
	python scripts/ci/verify_figures.py

field-study:
	python scripts/ci/verify_field_study.py

materialize-corpus:
	python scripts/ops/materialize_tenant_corpus.py --clean

deploy-helm-local:
	python scripts/ops/deploy_helm_local.py

ingest-corpus:
	python scripts/ci/verify_corpus_ingest.py

corpus-batch:
	python scripts/ci/verify_corpus_batch.py

live-hooks:
	python scripts/ci/verify_live_hooks.py

helm-deploy:
	python scripts/ci/verify_helm_deploy.py

certs:
	python scripts/ops/generate_dev_certs.py

stack-tls:
	python scripts/ops/generate_dev_certs.py
	docker compose -f docker-compose.tls.yml up --build

observability:
	python scripts/ci/verify_observability.py

hardening:
	python scripts/ci/verify_production_hardening.py

auth:
	python scripts/ci/verify_auth.py

release:
	python scripts/ops/package_release.py

verify-release: release
	python scripts/ci/verify_release.py

mtls:
	python scripts/ci/verify_mtls.py

stack-mtls:
	python scripts/ops/generate_dev_certs.py
	docker compose -f docker-compose.mtls.yml up --build

mypy:
	mypy packages/cfi_core/src packages/cfi_contributor/src packages/cfi_registry/src packages/cfi_recipient/src packages/cfi_federation/src packages/cfi_governance/src packages/cfi_cli/src services/replay_common.py services/registry services/coordinator services/aggregator services/integrations/replay services/integrations/agentrx services/integrations/causalflow services/integrations/tau

stack:
	docker compose up --build

stack-postgres:
	docker compose -f docker-compose.postgres.yml up --build

console:
	python scripts/ci/verify_dashboard.py

console-dev:
	cd apps/console && npm install && npm run dev

console-build:
	cd apps/console && npm install && npm run build
