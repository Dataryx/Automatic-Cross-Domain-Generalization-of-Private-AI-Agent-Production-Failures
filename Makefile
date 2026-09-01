# CFI-Fed developer commands

.PHONY: install test sim dod golden tau stack stack-postgres health

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

mypy:
	mypy packages/cfi_core/src packages/cfi_contributor/src packages/cfi_registry/src packages/cfi_recipient/src packages/cfi_federation/src packages/cfi_governance/src packages/cfi_cli/src

stack:
	docker compose up --build

stack-postgres:
	docker compose -f docker-compose.postgres.yml up --build
