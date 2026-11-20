.PHONY: help install dev lint format typecheck test coverage clean doctor

help:
	@echo "AuditIQ Development Commands:"
	@echo "  make install     Install project dependencies"
	@echo "  make dev         Install project in editable mode with dev dependencies"
	@echo "  make lint        Run ruff linter"
	@echo "  make format      Format code with ruff"
	@echo "  make typecheck   Run mypy static type checking"
	@echo "  make test        Run unit and integration tests"
	@echo "  make coverage    Run tests with coverage report"
	@echo "  make clean       Remove temporary files and caches"
	@echo "  make doctor      Check environment prerequisites"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	playwright install chromium

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

typecheck:
	mypy src tests

test:
	pytest

coverage:
	pytest --cov=auditiq --cov-report=term-missing --cov-report=html

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build *.egg-info

doctor:
	python -m auditiq doctor
