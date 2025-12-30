# Docker Test Environment Specification

**Issue**: [#367](https://github.com/pongogo/pongogo/issues/367) (Design)
**Implementation**: To be created as sub-issue of #320
**Created**: 2025-12-30

---

## Overview

This document specifies the Docker container configuration for running all test layers (unit, integration, E2E) in pongogo-to-go.

**Key Decision**: Docker for ALL test layers - same container for local and CI execution.

---

## 1. Dockerfile Specification

### Multi-Stage Build Design

```dockerfile
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

# Install additional test tools
RUN pip install --no-cache-dir \
    pytest-docker>=2.0.0 \
    pytest-asyncio>=0.21.0

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
```

### Stage Descriptions

| Stage | Purpose | Size |
|-------|---------|------|
| `base` | Production-equivalent environment | ~200MB |
| `test` | Full test environment with dev deps | ~250MB |

### Build Commands

```bash
# Build test image
docker build -t pongogo-test -f tests/Dockerfile --target test .

# Build production image (existing Dockerfile)
docker build -t pongogo-server .
```

---

## 2. Volume Mount Strategy

### Mount Points

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./tests/fixtures/` | `/app/tests/fixtures/` | Static test fixtures |
| `./tests/` | `/app/tests/` | Test source files (dev mode) |
| `./src/` | `/app/src/` | Source code (dev mode) |

### Test Fixture Structure

```
tests/
├── fixtures/
│   ├── minimal-project/           # Empty project for init tests
│   │   └── .gitkeep
│   │
│   ├── initialized-project/       # Post-init project state
│   │   └── .pongogo/
│   │       ├── config.yaml
│   │       └── instructions/
│   │           └── manifest.yaml
│   │
│   └── sample-instructions/       # Known routing test cases
│       ├── software_engineering/
│       │   └── test_instruction.md
│       └── project_management/
│           └── test_instruction.md
│
├── conftest.py                    # Shared pytest fixtures
├── unit/                          # Unit tests
├── integration/                   # Integration tests
└── e2e/                           # E2E tests
```

### Volume Mount Commands

```bash
# Development mode (live reload)
docker run -v $(pwd)/src:/app/src:ro \
           -v $(pwd)/tests:/app/tests:ro \
           pongogo-test

# CI mode (baked into image)
docker run pongogo-test
```

---

## 3. Environment Variable Configuration

### Test Mode Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PONGOGO_TEST_MODE` | `0` | Enable test mode (1=enabled) |
| `PONGOGO_KNOWLEDGE_PATH` | `/project/.pongogo/instructions` | Path to instruction files |
| `PONGOGO_LOG_LEVEL` | `INFO` | Logging level (DEBUG for tests) |
| `PYTHONUNBUFFERED` | `1` | Disable output buffering |

### Test-Specific Overrides

```bash
# Run with debug logging
docker run -e PONGOGO_LOG_LEVEL=DEBUG pongogo-test

# Use custom instruction path
docker run -e PONGOGO_KNOWLEDGE_PATH=/custom/path pongogo-test

# Disable test mode (production behavior validation)
docker run -e PONGOGO_TEST_MODE=0 pongogo-test
```

---

## 4. Container Startup/Shutdown Patterns

### pytest-docker Integration

```python
# tests/conftest.py

import pytest
import docker

@pytest.fixture(scope="session")
def docker_client():
    """Provide Docker client for container management."""
    return docker.from_env()

@pytest.fixture(scope="session")
def pongogo_server(docker_client):
    """Start Pongogo MCP server container for E2E tests."""
    container = docker_client.containers.run(
        "pongogo-server:test",
        detach=True,
        environment={
            "PONGOGO_TEST_MODE": "1",
            "PONGOGO_KNOWLEDGE_PATH": "/app/tests/fixtures/sample-instructions",
        },
        volumes={
            str(Path(__file__).parent / "fixtures"): {
                "bind": "/app/tests/fixtures",
                "mode": "ro"
            }
        },
        ports={"8000/tcp": None},  # Random available port
    )

    # Wait for server to be ready
    _wait_for_server(container)

    yield container

    # Cleanup
    container.stop()
    container.remove()

def _wait_for_server(container, timeout=30):
    """Wait for MCP server to accept connections."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            # Check if container is running
            container.reload()
            if container.status == "running":
                # Could add health check here
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise TimeoutError("Server did not start in time")
```

### Lifecycle Patterns

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| **Session-scoped** | E2E tests | Container starts once, shared across all E2E tests |
| **Function-scoped** | Integration tests | Fresh container per test function |
| **No container** | Unit tests | Direct Python imports, no Docker needed |

### Cleanup Strategy

```python
@pytest.fixture(scope="function")
def clean_fixture_state():
    """Reset fixture state between tests."""
    fixture_dir = Path(__file__).parent / "fixtures" / "initialized-project"

    # Backup original state
    original_state = _capture_state(fixture_dir)

    yield fixture_dir

    # Restore original state
    _restore_state(fixture_dir, original_state)
```

---

## 5. Multi-Platform Support

### Build Matrix

| Platform | Architecture | CI Runner |
|----------|--------------|-----------|
| Linux | amd64 | `ubuntu-latest` |
| Linux | arm64 | `ubuntu-24.04-arm` |
| macOS | arm64 | `macos-latest` (local dev) |

### Multi-Platform Build

```bash
# Build for multiple platforms
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t pongogo-test:latest \
    -f tests/Dockerfile \
    --target test \
    .
```

---

## 6. CI Integration

### GitHub Actions Usage

```yaml
# .github/workflows/ci.yml (excerpt)
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build test container
        run: |
          docker build -t pongogo-test \
            -f tests/Dockerfile \
            --target test .

      - name: Run tests
        run: |
          docker run --rm \
            -v ${{ github.workspace }}/coverage:/app/coverage \
            pongogo-test \
            pytest tests/ -v --cov=src --cov-report=xml:/app/coverage/coverage.xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/coverage.xml
```

---

## 7. Local Development Workflow

### Quick Commands

```bash
# Run all tests
docker build -t pongogo-test -f tests/Dockerfile --target test . && \
docker run --rm pongogo-test

# Run specific test file
docker run --rm pongogo-test pytest tests/unit/test_config.py -v

# Run with live code reload (development)
docker run --rm \
    -v $(pwd)/src:/app/src:ro \
    -v $(pwd)/tests:/app/tests:ro \
    pongogo-test pytest tests/ -v

# Interactive debugging
docker run --rm -it pongogo-test /bin/bash
```

### Makefile Targets (Recommended)

```makefile
# Makefile
.PHONY: test test-unit test-integration test-e2e

test-build:
	docker build -t pongogo-test -f tests/Dockerfile --target test .

test: test-build
	docker run --rm pongogo-test

test-unit: test-build
	docker run --rm pongogo-test pytest tests/unit/ -v

test-integration: test-build
	docker run --rm pongogo-test pytest tests/integration/ -v

test-e2e: test-build
	docker run --rm pongogo-test pytest tests/e2e/ -v

test-cov: test-build
	docker run --rm -v $(PWD)/htmlcov:/app/htmlcov \
		pongogo-test pytest tests/ --cov=src --cov-report=html:/app/htmlcov
```

---

## 8. Test Isolation Guarantees

### What's Isolated

| Aspect | Isolation Level | Mechanism |
|--------|-----------------|-----------|
| File system | Complete | Container has own filesystem |
| Network | Complete | Container network namespace |
| Environment | Complete | Container environment variables |
| Python packages | Complete | Container-installed packages |
| System state | Complete | No host system modification |

### What's Shared

| Aspect | Shared With | Purpose |
|--------|-------------|---------|
| Docker socket | Host | For pytest-docker to spawn containers |
| Mounted volumes | Host | For live code reload in dev mode |

---

## Implementation Checklist

When implementing this specification in #320:

- [ ] Create `tests/Dockerfile` with multi-stage build
- [ ] Create `tests/fixtures/` directory structure
- [ ] Create `tests/conftest.py` with Docker fixtures
- [ ] Add pytest-docker to dev dependencies
- [ ] Create Makefile with test targets
- [ ] Test multi-platform builds locally
- [ ] Verify CI integration works

---

## References

- Parent Spike: [#362](https://github.com/pongogo/pongogo/issues/362)
- Strategic Analysis: `docs/research/spike_362_test_architecture_analysis.md`
- Production Dockerfile: `Dockerfile` (root)
- pytest-docker: https://github.com/avast/pytest-docker
