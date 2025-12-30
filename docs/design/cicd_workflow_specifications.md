# CI/CD Workflow Specifications

**Issue**: [#372](https://github.com/pongogo/pongogo/issues/372) (Design)
**Implementation**: To be created as sub-issue of #320
**Created**: 2025-12-30

---

## Overview

This document specifies the complete GitHub Actions workflow configuration for pongogo-to-go, aligned with the release train model (alpha/beta/stable channels).

**Core Principle**: Same Docker container for local and CI execution - consistent test results everywhere.

---

## Workflow Summary

| File | Trigger | Purpose | Duration |
|------|---------|---------|----------|
| `ci.yml` | push, PR | Run all tests in Docker | ~10 min |
| `docker.yml` | push to main, tags | Build and push Docker image | ~5 min |
| `release-alpha.yml` | push to main | Tag alpha release | ~2 min |
| `release-beta.yml` | manual | Promote to beta channel | ~3 min |
| `release-stable.yml` | manual | Promote to stable channel | ~3 min |
| `deploy.yml` | release | Deploy install.sh | ~2 min |

---

## 1. ci.yml - Continuous Integration

### Purpose

Run all test layers in Docker container on every push and PR.

### Specification

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, beta, stable]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # =========================================================================
  # Pre-commit Hooks (Lint, Format, Type Check)
  # =========================================================================
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run pre-commit
        uses: pre-commit/action@v3.0.1
        with:
          extra_args: --all-files --show-diff-on-failure

  # =========================================================================
  # Build Test Container
  # =========================================================================
  build-test-image:
    name: Build Test Image
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build test image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: tests/Dockerfile
          target: test
          push: false
          load: true
          tags: pongogo-test:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Save image
        run: docker save pongogo-test:${{ github.sha }} | gzip > /tmp/test-image.tar.gz

      - name: Upload image artifact
        uses: actions/upload-artifact@v4
        with:
          name: test-image
          path: /tmp/test-image.tar.gz
          retention-days: 1

  # =========================================================================
  # Unit Tests
  # =========================================================================
  unit-tests:
    name: Unit Tests
    needs: build-test-image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download image artifact
        uses: actions/download-artifact@v4
        with:
          name: test-image
          path: /tmp

      - name: Load image
        run: gunzip -c /tmp/test-image.tar.gz | docker load

      - name: Run unit tests
        run: |
          docker run --rm \
            -v ${{ github.workspace }}/coverage:/app/coverage \
            pongogo-test:${{ github.sha }} \
            pytest tests/unit/ -v \
              --cov=src \
              --cov-report=xml:/app/coverage/unit-coverage.xml \
              --cov-fail-under=80 \
              --junitxml=/app/coverage/unit-results.xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/unit-coverage.xml
          flags: unit
          fail_ci_if_error: false

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: unit-test-results
          path: coverage/unit-results.xml

  # =========================================================================
  # Integration Tests
  # =========================================================================
  integration-tests:
    name: Integration Tests
    needs: build-test-image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download image artifact
        uses: actions/download-artifact@v4
        with:
          name: test-image
          path: /tmp

      - name: Load image
        run: gunzip -c /tmp/test-image.tar.gz | docker load

      - name: Run integration tests
        run: |
          docker run --rm \
            -v ${{ github.workspace }}/coverage:/app/coverage \
            pongogo-test:${{ github.sha }} \
            pytest tests/integration/ -v \
              --cov=src \
              --cov-report=xml:/app/coverage/integration-coverage.xml \
              --junitxml=/app/coverage/integration-results.xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/integration-coverage.xml
          flags: integration
          fail_ci_if_error: false

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: integration-test-results
          path: coverage/integration-results.xml

  # =========================================================================
  # E2E Tests
  # =========================================================================
  e2e-tests:
    name: E2E Tests
    needs: [unit-tests, integration-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download image artifact
        uses: actions/download-artifact@v4
        with:
          name: test-image
          path: /tmp

      - name: Load image
        run: gunzip -c /tmp/test-image.tar.gz | docker load

      - name: Run E2E tests
        run: |
          docker run --rm \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v ${{ github.workspace }}/coverage:/app/coverage \
            pongogo-test:${{ github.sha }} \
            pytest tests/e2e/ -v \
              --junitxml=/app/coverage/e2e-results.xml

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: e2e-test-results
          path: coverage/e2e-results.xml

  # =========================================================================
  # Final Status Check
  # =========================================================================
  ci-success:
    name: CI Success
    needs: [lint, unit-tests, integration-tests, e2e-tests]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Check all jobs passed
        run: |
          if [[ "${{ needs.lint.result }}" != "success" ]] || \
             [[ "${{ needs.unit-tests.result }}" != "success" ]] || \
             [[ "${{ needs.integration-tests.result }}" != "success" ]] || \
             [[ "${{ needs.e2e-tests.result }}" != "success" ]]; then
            echo "One or more jobs failed"
            exit 1
          fi
          echo "All CI jobs passed!"
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Build once, test many | Single test image shared across all test jobs |
| Artifact sharing | Pass Docker image between jobs via artifacts |
| Parallel execution | Unit and integration tests run in parallel |
| Sequential E2E | E2E runs after unit/integration to save resources |
| Coverage gating | 80% minimum for unit tests |

---

## 2. docker.yml - Docker Image Build

### Purpose

Build and push production Docker image to GitHub Container Registry (GHCR).

### Specification

```yaml
# .github/workflows/docker.yml
name: Docker Build

on:
  push:
    branches: [main]
    tags: ["v*"]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    name: Build & Push
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Multi-Platform Build Matrix

| Platform | Architecture | Use Case |
|----------|--------------|----------|
| linux/amd64 | x86_64 | CI runners, most servers |
| linux/arm64 | ARM64 | Apple Silicon, ARM servers |

---

## 3. release-alpha.yml - Alpha Releases

### Purpose

Automatically create alpha releases on every push to main. Alpha is the bleeding-edge channel for internal testing.

### Specification

```yaml
# .github/workflows/release-alpha.yml
name: Alpha Release

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  alpha-release:
    name: Create Alpha Release
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get version info
        id: version
        run: |
          # Get short SHA
          SHORT_SHA=$(git rev-parse --short HEAD)
          # Get date in YYYYMMDD format
          DATE=$(date +%Y%m%d)
          # Create alpha version
          VERSION="alpha-${DATE}-${SHORT_SHA}"
          echo "version=${VERSION}" >> $GITHUB_OUTPUT
          echo "tag=v${VERSION}" >> $GITHUB_OUTPUT

      - name: Check if tag exists
        id: check-tag
        run: |
          if git rev-parse "${{ steps.version.outputs.tag }}" >/dev/null 2>&1; then
            echo "exists=true" >> $GITHUB_OUTPUT
          else
            echo "exists=false" >> $GITHUB_OUTPUT
          fi

      - name: Create alpha tag
        if: steps.check-tag.outputs.exists == 'false'
        run: |
          git tag ${{ steps.version.outputs.tag }}
          git push origin ${{ steps.version.outputs.tag }}

      - name: Create GitHub Release
        if: steps.check-tag.outputs.exists == 'false'
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ steps.version.outputs.tag }}
          name: Alpha ${{ steps.version.outputs.version }}
          prerelease: true
          generate_release_notes: true
          body: |
            ## Alpha Release

            **Channel**: Alpha (internal testing)
            **Commit**: ${{ github.sha }}

            This is an automated alpha release. Use for internal testing only.

            ### Install

            ```bash
            pip install pongogo==${{ steps.version.outputs.version }}
            ```

            Or use Docker:
            ```bash
            docker pull ghcr.io/${{ github.repository }}:${{ steps.version.outputs.tag }}
            ```
```

### Alpha Release Cadence

| Trigger | Frequency | Artifact |
|---------|-----------|----------|
| Push to main | On every commit | `alpha-YYYYMMDD-SHORTSHA` |

---

## 4. release-beta.yml - Beta Releases

### Purpose

Manual promotion from main to beta channel. Beta is the dogfooding channel for Pongogo development.

### Specification

```yaml
# .github/workflows/release-beta.yml
name: Beta Release

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Beta version (e.g., 0.1.0)'
        required: true
        type: string
      notes:
        description: 'Release notes'
        required: false
        type: string
        default: ''

jobs:
  validate:
    name: Validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate version format
        run: |
          if ! [[ "${{ inputs.version }}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Error: Version must be in semver format (X.Y.Z)"
            exit 1
          fi

      - name: Check CI status
        run: |
          # Get latest workflow run for main branch
          STATUS=$(gh run list --branch main --workflow ci.yml --limit 1 --json conclusion -q '.[0].conclusion')
          if [[ "$STATUS" != "success" ]]; then
            echo "Error: CI must pass before beta release"
            exit 1
          fi
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  beta-release:
    name: Create Beta Release
    needs: validate
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write

    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
          fetch-depth: 0

      - name: Configure Git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Merge main to beta
        run: |
          git checkout beta || git checkout -b beta
          git merge main --no-edit -m "Merge main into beta for v${{ inputs.version }}-beta"
          git push origin beta

      - name: Create beta tag
        run: |
          TAG="v${{ inputs.version }}-beta"
          git tag -a "$TAG" -m "Beta release ${{ inputs.version }}"
          git push origin "$TAG"

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: v${{ inputs.version }}-beta
          name: Beta ${{ inputs.version }}
          prerelease: true
          body: |
            ## Beta Release

            **Channel**: Beta (dogfooding)
            **Version**: ${{ inputs.version }}

            This is a beta release for Pongogo development. Used internally for dogfooding.

            ${{ inputs.notes }}

            ### Install

            ```bash
            pip install pongogo==${{ inputs.version }}b0
            ```

            Or use Docker:
            ```bash
            docker pull ghcr.io/${{ github.repository }}:v${{ inputs.version }}-beta
            ```

            ### Update stage0 config

            After installing, update `.pongogo-stage0.json`:
            ```json
            {
              "version": "${{ inputs.version }}-beta"
            }
            ```

      - name: Trigger Docker build
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.actions.createWorkflowDispatch({
              owner: context.repo.owner,
              repo: context.repo.repo,
              workflow_id: 'docker.yml',
              ref: 'v${{ inputs.version }}-beta'
            })
```

### Beta Release Process

```
1. Developer triggers workflow_dispatch
   └── Input: version (e.g., "0.2.0")

2. Validation
   ├── Check version format (semver)
   └── Verify CI passing on main

3. Merge and Tag
   ├── Merge main → beta
   └── Create v{version}-beta tag

4. Release
   ├── Create GitHub Release (prerelease=true)
   └── Trigger Docker build for tag
```

---

## 5. release-stable.yml - Stable Releases

### Purpose

Manual promotion from beta to stable channel. Stable is the production channel for external users.

### Specification

```yaml
# .github/workflows/release-stable.yml
name: Stable Release

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Stable version (e.g., 0.1.0)'
        required: true
        type: string
      beta_version:
        description: 'Beta version to promote (e.g., 0.1.0)'
        required: true
        type: string
      notes:
        description: 'Release notes'
        required: false
        type: string
        default: ''

jobs:
  validate:
    name: Validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate version format
        run: |
          if ! [[ "${{ inputs.version }}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Error: Version must be in semver format (X.Y.Z)"
            exit 1
          fi

      - name: Check beta tag exists
        run: |
          if ! git rev-parse "v${{ inputs.beta_version }}-beta" >/dev/null 2>&1; then
            echo "Error: Beta tag v${{ inputs.beta_version }}-beta does not exist"
            exit 1
          fi

  stable-release:
    name: Create Stable Release
    needs: validate
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write

    steps:
      - uses: actions/checkout@v4
        with:
          ref: beta
          fetch-depth: 0

      - name: Configure Git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Merge beta to stable
        run: |
          git checkout stable || git checkout -b stable
          git merge v${{ inputs.beta_version }}-beta --no-edit -m "Merge beta ${{ inputs.beta_version }} into stable for v${{ inputs.version }}"
          git push origin stable

      - name: Create stable tag
        run: |
          TAG="v${{ inputs.version }}"
          git tag -a "$TAG" -m "Stable release ${{ inputs.version }}"
          git push origin "$TAG"

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: v${{ inputs.version }}
          name: Release ${{ inputs.version }}
          prerelease: false
          body: |
            ## Stable Release

            **Channel**: Stable (production)
            **Version**: ${{ inputs.version }}
            **Promoted from**: Beta ${{ inputs.beta_version }}

            This is a production-ready stable release.

            ${{ inputs.notes }}

            ### Install

            ```bash
            pip install pongogo==${{ inputs.version }}
            ```

            Or use Docker:
            ```bash
            docker pull ghcr.io/${{ github.repository }}:v${{ inputs.version }}
            # Or latest stable:
            docker pull ghcr.io/${{ github.repository }}:stable
            ```

            ### Quick Start

            ```bash
            # Install
            curl -sSL https://get.pongogo.com | bash

            # Initialize in your project
            cd your-project
            pongogo init

            # Configure Claude Code
            pongogo setup-mcp
            ```

      - name: Tag as latest stable
        run: |
          docker pull ghcr.io/${{ github.repository }}:v${{ inputs.version }}
          docker tag ghcr.io/${{ github.repository }}:v${{ inputs.version }} ghcr.io/${{ github.repository }}:stable
          docker push ghcr.io/${{ github.repository }}:stable

      - name: Trigger deploy
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.actions.createWorkflowDispatch({
              owner: context.repo.owner,
              repo: context.repo.repo,
              workflow_id: 'deploy.yml',
              ref: 'v${{ inputs.version }}'
            })
```

---

## 6. deploy.yml - Deploy Install Script

### Purpose

Deploy the install script to get.pongogo.com on stable releases.

### Specification

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version being deployed'
        required: true
        type: string
  release:
    types: [published]

jobs:
  deploy-install-script:
    name: Deploy Install Script
    runs-on: ubuntu-latest
    if: |
      github.event_name == 'workflow_dispatch' ||
      (github.event_name == 'release' && !github.event.release.prerelease)

    steps:
      - uses: actions/checkout@v4

      - name: Get version
        id: version
        run: |
          if [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
            echo "version=${{ inputs.version }}" >> $GITHUB_OUTPUT
          else
            echo "version=${{ github.event.release.tag_name }}" >> $GITHUB_OUTPUT
          fi

      - name: Prepare install script
        run: |
          # Update version in install script
          sed -i "s/PONGOGO_VERSION=.*/PONGOGO_VERSION=\"${{ steps.version.outputs.version }}\"/" scripts/install.sh
          # Verify script is valid
          bash -n scripts/install.sh

      - name: Deploy to Azure Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "scripts"
          skip_app_build: true
          output_location: ""
```

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Stable Release                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     deploy.yml                                   │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ Get Version │→ │ Update Script   │→ │ Deploy to Azure     │  │
│  │             │  │ with version    │  │ Static Web Apps     │  │
│  └─────────────┘  └─────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              https://get.pongogo.com                            │
│              └── install.sh                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Secrets and Permissions

### Required Secrets

| Secret | Purpose | Where Used |
|--------|---------|------------|
| `GITHUB_TOKEN` | Auto-provided | All workflows |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | Azure deployment | deploy.yml |
| `CODECOV_TOKEN` | Coverage uploads | ci.yml |

### Permissions Matrix

| Workflow | Permissions |
|----------|-------------|
| ci.yml | `contents: read`, `packages: read` |
| docker.yml | `contents: read`, `packages: write` |
| release-alpha.yml | `contents: write`, `packages: write` |
| release-beta.yml | `contents: write`, `packages: write` |
| release-stable.yml | `contents: write`, `packages: write` |
| deploy.yml | `contents: read` |

---

## Release Channel Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         main branch                              │
│  ┌──────────┐                                                    │
│  │  Commit  │ ────────────────────────────────────────────────▶  │
│  └──────────┘                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────┐      ┌───────────────────┐                    │
│  │    ci.yml    │ ──▶  │ release-alpha.yml │ ──▶ Alpha Release  │
│  │  (on push)   │      │   (on push)       │     v-alpha-DATE   │
│  └──────────────┘      └───────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ Manual trigger (workflow_dispatch)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         beta branch                              │
│  ┌───────────────────┐                                          │
│  │ release-beta.yml  │ ──▶ Beta Release                         │
│  │ (manual trigger)  │     v0.X.Y-beta                          │
│  └───────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ Manual trigger (workflow_dispatch)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        stable branch                             │
│  ┌────────────────────┐      ┌──────────────┐                   │
│  │ release-stable.yml │ ──▶  │  deploy.yml  │ ──▶ get.pongogo   │
│  │ (manual trigger)   │      │  (on stable) │     .com          │
│  └────────────────────┘      └──────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Test Matrix

### CI Test Matrix

```yaml
# Python versions and platforms for CI
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
    os: [ubuntu-latest]
  fail-fast: false
```

### Docker Build Matrix

```yaml
# Multi-platform Docker builds
platforms: linux/amd64,linux/arm64
```

### Test Layer Execution Order

```
Pre-commit (lint, format, type) ──────────────────────▶ ~30s
                                          │
                                          ▼
                              ┌───────────────────┐
                              │ Build Test Image  │ ────▶ ~2min
                              └───────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                                 ▼
             ┌────────────┐                    ┌────────────┐
             │ Unit Tests │                    │ Integration│
             │   ~60s     │                    │   ~3min    │
             └────────────┘                    └────────────┘
                    │                                 │
                    └────────────────┬────────────────┘
                                     ▼
                              ┌────────────┐
                              │ E2E Tests  │ ────▶ ~5min
                              └────────────┘
                                     │
                                     ▼
                              CI Success Gate
```

---

## Implementation Checklist

When implementing this specification in #320:

- [ ] Create `.github/workflows/ci.yml`
- [ ] Create `.github/workflows/docker.yml`
- [ ] Create `.github/workflows/release-alpha.yml`
- [ ] Create `.github/workflows/release-beta.yml`
- [ ] Create `.github/workflows/release-stable.yml`
- [ ] Create `.github/workflows/deploy.yml`
- [ ] Create `beta` and `stable` branches
- [ ] Configure GHCR access (packages permissions)
- [ ] Add Azure deployment secret
- [ ] Test full release flow (alpha → beta → stable)
- [ ] Verify multi-platform Docker builds

---

## References

- Parent Spike: [#362](https://github.com/pongogo/pongogo/issues/362)
- Release Train Architecture: `docs/decisions/release_train_architecture.md`
- Docker Environment: `docs/design/docker_test_environment.md`
- Test Pyramid: `docs/design/test_pyramid_layers.md`
- Pre-commit Config: `docs/design/precommit_configuration.md`
