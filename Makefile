# CFI-Fed developer commands

.PHONY: install test sim dod golden tau tau-live agent-hooks cross-boundary corpus-publish end-to-end federation full-pipeline compose-full-pipeline postgres-compose-full-pipeline tls-full-pipeline mtls-full-pipeline stack stack-postgres stack-tls stack-mtls health live-replay replay-profiles eval-harnesses compose-smoke postgres-smoke helm-chart remote-registry contribute-publish audit-attest mypy figures field-study ingest-corpus eval-all certs observability hardening auth release verify-release mtls

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -q

sim:
	python sim/run_cfi_sim.py
	python scripts/verify_sim.py

dod:
	python eval/verify_dod.py

golden:
	python scripts/golden_path.py

tau:
	python eval/benchmarks/tau_adapter.py

tau-live:
	python scripts/verify_tau_live.py

eval-all:
	python eval/run_all.py

health:
	python scripts/health_check.py

live-replay:
	python scripts/live_replay_smoke.py

replay-profiles:
	python scripts/verify_replay_profiles.py

eval-harnesses:
	python scripts/verify_eval_harnesses.py

compose-smoke:
	python scripts/verify_compose_stack.py

postgres-smoke:
	python scripts/verify_postgres_compose.py

helm-chart:
	python scripts/verify_helm_chart.py

remote-registry:
	python scripts/verify_remote_registry_cli.py

contribute-publish:
	python scripts/verify_contribute_publish.py

agent-hooks:
	python scripts/verify_agent_hooks.py

cross-boundary:
	python scripts/verify_cross_boundary.py

corpus-publish:
	python scripts/verify_corpus_publish.py

end-to-end:
	python scripts/verify_end_to_end.py

federation:
	python scripts/verify_federation_workflow.py

full-pipeline:
	python scripts/verify_full_pipeline.py

cli-endpoints:
	python scripts/verify_cli_endpoints.py

pipeline-matrix:
	python scripts/verify_pipeline_matrix.py

compose-full-pipeline:
	python scripts/verify_compose_full_pipeline.py

postgres-compose-full-pipeline:
	python scripts/verify_postgres_compose_full_pipeline.py

tls-full-pipeline:
	python scripts/verify_tls_full_pipeline.py

mtls-full-pipeline:
	python scripts/verify_mtls_full_pipeline.py

postgres-tls-full-pipeline:
	python scripts/verify_postgres_tls_full_pipeline.py

mtls-required-full-pipeline:
	python scripts/verify_mtls_required_full_pipeline.py

pipeline-matrix-ci:
	CFI_REQUIRE_DOCKER=1 python scripts/verify_pipeline_matrix_ci.py

audit-attest:
	python scripts/verify_audit_attestation.py

figures:
	python scripts/verify_figures.py

field-study:
	python scripts/verify_field_study.py

materialize-corpus:
	python scripts/materialize_tenant_corpus.py --clean

deploy-helm-local:
	python scripts/deploy_helm_local.py

ingest-corpus:
	python scripts/verify_corpus_ingest.py

corpus-batch:
	python scripts/verify_corpus_batch.py

live-hooks:
	python scripts/verify_live_hooks.py

helm-deploy:
	python scripts/verify_helm_deploy.py

certs:
	python scripts/generate_dev_certs.py

stack-tls:
	python scripts/generate_dev_certs.py
	docker compose -f docker-compose.tls.yml up --build

observability:
	python scripts/verify_observability.py

hardening:
	python scripts/verify_production_hardening.py

auth:
	python scripts/verify_auth.py

release:
	python scripts/package_release.py

verify-release: release
	python scripts/verify_release.py

mtls:
	python scripts/verify_mtls.py

stack-mtls:
	python scripts/generate_dev_certs.py
	docker compose -f docker-compose.mtls.yml up --build

mypy:
	mypy packages/cfi_core/src packages/cfi_contributor/src packages/cfi_registry/src packages/cfi_recipient/src packages/cfi_federation/src packages/cfi_governance/src packages/cfi_cli/src services/replay_common.py services/registry services/coordinator services/aggregator services/replay_mock services/agentrx_stub services/causalflow_stub services/tau_stub

stack:
	docker compose up --build

stack-postgres:
	docker compose -f docker-compose.postgres.yml up --build
