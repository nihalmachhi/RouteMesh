PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.PHONY: install lint typecheck test check up down bench format
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
	$(PYTHON) -m routemesh.benchmarks.run_benchmark
