# CFI-Fed developer commands

.PHONY: install test sim dod golden tau stack stack-postgres stack-tls stack-mtls health live-replay mypy figures field-study ingest-corpus eval-all certs observability hardening auth release mtls

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

eval-all:
	python eval/run_all.py

health:
	python scripts/health_check.py

live-replay:
	python scripts/live_replay_smoke.py

figures:
	python scripts/verify_figures.py

field-study:
	python scripts/verify_field_study.py

ingest-corpus:
	python scripts/verify_corpus_ingest.py

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

mtls:
	python scripts/verify_mtls.py

stack-mtls:
	python scripts/generate_dev_certs.py
	docker compose -f docker-compose.mtls.yml up --build

mypy:
	mypy packages/cfi_core/src packages/cfi_contributor/src packages/cfi_registry/src packages/cfi_recipient/src packages/cfi_federation/src packages/cfi_governance/src packages/cfi_cli/src

stack:
	docker compose up --build

stack-postgres:
	docker compose -f docker-compose.postgres.yml up --build
