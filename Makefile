PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.PHONY: install lint typecheck test check up down bench bench-sim reproduce site-fixtures format
install:
	$(PIP) install -e ".[dev]"
lint:
	ruff check src tests
format:
	ruff format src tests
typecheck:
	mypy src
test:
	pytest
check: lint typecheck test
up:
	docker compose up --build
down:
	docker compose down
bench:
	$(PYTHON) -m benchmarks.run_benchmark
bench-sim:
	$(PYTHON) -m routemesh.sim.report
reproduce:
	$(PYTHON) -m routemesh.sim.report
	$(PYTHON) site/scripts/export_fixtures.py
site-fixtures:
	$(PYTHON) site/scripts/export_fixtures.py
