# Makefile for pongogo-to-go
# Development targets for linting, formatting, and testing

.PHONY: help install lint format typecheck pre-commit test clean
.PHONY: test-build test-docker test-unit test-integration test-e2e test-cov

# Default target
help:
	@echo "Available targets:"
	@echo "  install          Install package with dev dependencies"
	@echo "  lint             Run ruff linting"
	@echo "  format           Run ruff formatting"
	@echo "  typecheck        Run mypy type checking"
	@echo "  pre-commit       Run all pre-commit hooks"
	@echo "  test             Run pytest (native)"
	@echo "  test-build       Build Docker test image"
	@echo "  test-docker      Run all tests in Docker"
	@echo "  test-unit        Run unit tests in Docker"
	@echo "  test-integration Run integration tests in Docker"
	@echo "  test-e2e         Run E2E tests in Docker"
	@echo "  test-cov         Run tests with coverage report"
	@echo "  clean            Remove build artifacts"

# Install with dev dependencies
install:
	pip install -e ".[dev]"
	pre-commit install

# Run linting
lint:
	ruff check src/ tests/

# Run formatter
format:
	ruff format src/ tests/

# Run type checker
typecheck:
	mypy src/ tests/

# Run all pre-commit hooks
pre-commit:
	pre-commit run --all-files

# Run tests
test:
	pytest tests/ -v

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# =============================================================================
# Docker Test Targets
# =============================================================================

# Build Docker test image
test-build:
	docker build -t pongogo-test -f tests/Dockerfile --target test .

# Run all tests in Docker
test-docker: test-build
	docker run --rm pongogo-test

# Run unit tests in Docker
test-unit: test-build
	docker run --rm pongogo-test pytest tests/unit/ -v

# Run integration tests in Docker
test-integration: test-build
	docker run --rm pongogo-test pytest tests/integration/ -v

# Run E2E tests in Docker
test-e2e: test-build
	docker run --rm pongogo-test pytest tests/e2e/ -v

# Run tests with HTML coverage report
test-cov: test-build
	docker run --rm -v $(PWD)/htmlcov:/app/htmlcov \
		pongogo-test pytest tests/ --cov=src --cov-report=html:/app/htmlcov
	@echo "Coverage report: htmlcov/index.html"
