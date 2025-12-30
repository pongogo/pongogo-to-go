# tests/Dockerfile
# Test container for pongogo-to-go
# Extends production image with dev dependencies

# ============================================
# Stage 1: Base (production dependencies)
# ============================================
FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Copy package files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY instructions/ ./instructions/

# Install production dependencies
RUN pip install --no-cache-dir -e .

# ============================================
# Stage 2: Test (adds dev dependencies)
# ============================================
FROM base AS test

# Install dev/test dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy test files
COPY tests/ ./tests/

# Create test user (matches production security model)
RUN groupadd -r testuser && useradd -r -g testuser testuser
RUN chown -R testuser:testuser /app

# Test-specific environment
ENV PYTHONUNBUFFERED=1
ENV PONGOGO_TEST_MODE=1
ENV PONGOGO_KNOWLEDGE_PATH=/app/tests/fixtures/sample-instructions

USER testuser

# Default command runs all tests
CMD ["pytest", "tests/", "-v", "--cov=src", "--cov-report=term-missing"]
