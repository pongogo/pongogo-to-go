# Makefile for pongogo-to-go
# Development targets for linting, formatting, and testing

.PHONY: help install lint format typecheck pre-commit test clean

# Default target
help:
	@echo "Available targets:"
	@echo "  install     Install package with dev dependencies"
	@echo "  lint        Run ruff linting"
	@echo "  format      Run ruff formatting"
	@echo "  typecheck   Run mypy type checking"
	@echo "  pre-commit  Run all pre-commit hooks"
	@echo "  test        Run pytest"
	@echo "  clean       Remove build artifacts"

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
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
