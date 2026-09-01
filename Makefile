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

stack:
	docker compose up --build

stack-postgres:
	docker compose -f docker-compose.postgres.yml up --build
