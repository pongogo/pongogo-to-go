# Pongogo Deployment Architecture

**Last Updated**: 2026-01-01

This document provides a comprehensive overview of Pongogo's deployment infrastructure, CI/CD pipelines, testing architecture, and Azure services.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [CI/CD Pipelines](#cicd-pipelines)
3. [Azure Infrastructure](#azure-infrastructure)
4. [Test Pyramid](#test-pyramid)
5. [Docker Image Distribution](#docker-image-distribution)
6. [Install Script Flow](#install-script-flow)
7. [Release Channels](#release-channels)
8. [OIDC Authentication](#oidc-authentication)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GitHub Actions                                  │
├──────────────────┬──────────────────┬──────────────────┬───────────────────┤
│     ci.yml       │   docker.yml     │ release-*.yml    │    deploy.yml     │
│  (Tests & Lint)  │  (Build Images)  │ (Tag Releases)   │ (Install Script)  │
└────────┬─────────┴────────┬─────────┴────────┬─────────┴─────────┬─────────┘
         │                  │                  │                   │
         ▼                  ▼                  ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐
│   Test Image    │ │   GHCR          │ │   GitHub        │ │Azure Storage  │
│   (ephemeral)   │ │ghcr.io/pongogo/ │ │   Releases      │ │(get.pongogo)  │
└─────────────────┘ │pongogo-to-go    │ │   (Tags)        │ └───────┬───────┘
                    └────────┬────────┘ └─────────────────┘         │
                             │                                       │
                    ┌────────▼────────┐                     ┌───────▼───────┐
                    │   Azure ACR     │                     │  Azure CDN    │
                    │pongogo.azurecr  │                     │(Front Door)   │
                    │   .io/pongogo   │                     └───────────────┘
                    └─────────────────┘
```

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **GitHub Actions** | CI/CD automation | `.github/workflows/` |
| **GHCR** | GitHub Container Registry (private) | `ghcr.io/pongogo/pongogo-to-go` |
| **Azure ACR** | Public Docker registry (anonymous pull) | `pongogo.azurecr.io/pongogo` |
| **Azure Storage** | Static file hosting for install script | `pongogodownloads` |
| **Azure Front Door** | CDN for `get.pongogo.com` | `pongogo-cdn` |

---

## CI/CD Pipelines

### Workflow Overview

| Workflow | Trigger | Purpose | Duration |
|----------|---------|---------|----------|
| `ci.yml` | push, PR | Run tests in Docker | ~10 min |
| `docker.yml` | push main, tags | Build multi-arch images | ~5 min |
| `release-beta.yml` | push to main | Auto-create beta release | ~3 min |
| `release-stable.yml` | manual | Promote beta to stable | ~3 min |
| `deploy.yml` | manual, release | Deploy install script | ~2 min |

### ci.yml - Continuous Integration

**Purpose**: Run all test layers on every push and PR.

**Jobs**:
```
lint → (parallel) → unit-tests      → e2e-tests → ci-success
                  → integration-tests ↗
                                      ↗
build-test-image →──────────────────────────────→
```

**Key Features**:
- Pre-commit hooks (ruff, mypy)
- Shared test image via artifacts (build once, use everywhere)
- Unit and integration tests run in parallel
- E2E tests run after unit/integration pass
- Codecov integration for coverage reporting
- 5% coverage threshold (intentionally low during early development)

### docker.yml - Docker Build

**Purpose**: Build multi-platform Docker images and push to registries.

**Trigger**: Push to `main` branch or any `v*` tag.

**Platforms**: `linux/amd64`, `linux/arm64`

**Registries**:
| Registry | Authentication | Access |
|----------|----------------|--------|
| GHCR | `GITHUB_TOKEN` | Private (org members) |
| Azure ACR | OIDC (federated credentials) | Public (anonymous pull) |

**Tags Generated**:
| Event | Example Tags |
|-------|--------------|
| Push to main | `main`, `abc123` (SHA) |
| Tag `v0.1.0` | `0.1.0`, `0.1`, `latest` |
| Tag `vbeta-*` | `vbeta-20260101-abc123` |

### release-beta.yml - Beta Releases

**Purpose**: Automatically create beta releases from main.

**Trigger**: Every push to `main` branch.

**Flow**:
1. Generate version: `beta-YYYYMMDD-SHA`
2. Create tag: `vbeta-20260101-abc123`
3. Merge main → beta branch
4. Create GitHub prerelease
5. Trigger `docker.yml` to build images

**Tag Format**: `vbeta-YYYYMMDD-SHORTSHA`

### release-stable.yml - Stable Releases

**Purpose**: Promote a tested beta to stable.

**Trigger**: Manual workflow dispatch.

**Inputs**:
| Input | Example | Description |
|-------|---------|-------------|
| `version` | `0.1.0` | Semver version |
| `beta_tag` | `vbeta-20260101-abc123` | Beta tag to promote |
| `notes` | "Bug fixes" | Release notes |

**Flow**:
1. Validate version format and beta tag exists
2. Merge beta → stable branch
3. Create stable tag: `v0.1.0`
4. Create GitHub release (non-prerelease)
5. Build Docker images with `stable` and `latest` tags
6. Trigger `deploy.yml` to update install script

### deploy.yml - Install Script Deployment

**Purpose**: Deploy install script to `get.pongogo.com`.

**Trigger**: Manual dispatch or stable release publish.

**Flow**:
1. Generate `install.sh` with embedded install logic
2. Upload to Azure Storage `$web` container
3. Purge Azure CDN cache

---

## Azure Infrastructure

### Resource Group: `pongogo-rg`

### Azure Container Registry (ACR)

| Property | Value |
|----------|-------|
| Name | `pongogo` |
| Login Server | `pongogo.azurecr.io` |
| SKU | Standard (~$20/month) |
| Anonymous Pull | Enabled |

**Why Standard SKU?** Anonymous pull requires Standard tier (not available on Basic).

**Image Tags**:
| Tag | Meaning |
|-----|---------|
| `stable` | Latest stable release |
| `latest` | Same as stable |
| `main` | Latest from main branch |
| `v0.1.0` | Specific version |
| `vbeta-*` | Beta releases |

### Azure Storage Account

| Property | Value |
|----------|-------|
| Name | `pongogodownloads` |
| SKU | Standard_LRS |
| Static Website | Enabled |
| Container | `$web` |

**Files**:
| Path | Content-Type | Purpose |
|------|--------------|---------|
| `/index.html` | `text/html` | Redirect to install.sh |
| `/install.sh` | `text/x-shellscript` | Install script |

### Azure Front Door (CDN)

| Property | Value |
|----------|-------|
| Profile Name | `pongogo-cdn` |
| SKU | Standard_AzureFrontDoor |
| Endpoint | `pongogo-downloads` |
| Custom Domain | `get.pongogo.com` |
| Origin | `pongogodownloads.z13.web.core.windows.net` |

**Cache Behavior**: CDN caches content. Purge required on deploy.

### Azure Static Web App

| Property | Value |
|----------|-------|
| Name | `pongogo-homepage` |
| Custom Domains | `pongogo.com`, `www.pongogo.com` |
| Purpose | Main website (separate from installer) |

---

## Test Pyramid

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E╲           (~5 tests)
                 ╱──────╲          Full Docker workflows
                ╱        ╲
               ╱Integration╲       (~15 tests)
              ╱────────────╲       MCP server routing
             ╱              ╲
            ╱    Unit Tests  ╲     (~93 tests)
           ╱──────────────────╲    Fast, isolated
          ╱                    ╲
```

### Test Types

| Layer | Location | What It Tests | Isolation |
|-------|----------|---------------|-----------|
| Unit | `tests/unit/` | Functions, classes | Full mocking |
| Integration | `tests/integration/` | MCP server, routing | Real server, mock data |
| E2E | `tests/e2e/` | Full Docker workflows | Real containers |

### Test Infrastructure

**Test Dockerfile** (`tests/Dockerfile`):
- Extends production image
- Adds dev dependencies
- Non-root user for security
- Test fixtures included

**Test Environment Variables**:
```bash
PONGOGO_TEST_MODE=1
PONGOGO_KNOWLEDGE_PATH=/app/tests/fixtures/sample-instructions
```

### Coverage Requirements

| Layer | Current Target | Future Target |
|-------|----------------|---------------|
| Unit | 5% (bootstrap) | 80% |
| Integration | None | 70% |
| E2E | None | Key paths |

---

## Docker Image Distribution

### Dual Registry Strategy

Users pull from **ACR** (public), CI/CD pushes to **both**:

```
GitHub Actions
     │
     ├──────────────────► GHCR (private)
     │                    - Backup registry
     │                    - Org member access
     │
     └──────────────────► Azure ACR (public)
                          - User-facing registry
                          - Anonymous pull enabled
```

### Image Names

| Registry | Full Image Name | Pull Command |
|----------|-----------------|--------------|
| ACR | `pongogo.azurecr.io/pongogo:stable` | `docker pull pongogo.azurecr.io/pongogo:stable` |
| GHCR | `ghcr.io/pongogo/pongogo-to-go:stable` | Requires auth |

### Multi-Platform Support

Both `linux/amd64` and `linux/arm64` are built:
- Intel/AMD Macs and Linux
- Apple Silicon Macs (M1/M2/M3)

---

## Install Script Flow

**URL**: `https://get.pongogo.com`

```bash
curl -sSL https://get.pongogo.com | bash
```

### Flow Diagram

```
┌──────────────────┐
│ Check Docker     │
│ installed?       │
└────────┬─────────┘
         │ No
         ▼
┌──────────────────┐
│ Show install     │
│ instructions     │──► Exit
└──────────────────┘

         │ Yes
         ▼
┌──────────────────┐
│ Docker running?  │
└────────┬─────────┘
         │ No
         ▼
┌──────────────────┐
│ Ask: Start       │
│ Docker?          │
└────────┬─────────┘
         │ Yes
         ▼
┌──────────────────┐
│ Start Docker     │
│ (macOS/Linux)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Docker needs     │
│ sudo?            │
└────────┬─────────┘
         │ Yes
         ▼
┌──────────────────┐
│ Show docker      │
│ group setup      │──► Exit
└──────────────────┘

         │ No
         ▼
┌──────────────────┐
│ Pull ACR image   │
│ pongogo:stable   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Configure Claude │
│ Code MCP server  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Create CLI       │
│ ~/.local/bin/    │
│ pongogo wrapper  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ In git repo?     │
└────────┬─────────┘
         │ Yes
         ▼
┌──────────────────┐
│ Ask: Run         │
│ pongogo init?    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Done!            │
└──────────────────┘
```

### Key Behaviors

**Interactive Prompts**: Use `< /dev/tty` because stdin is the script in `curl | bash`.

**Docker Group Requirement**: Linux users must be in docker group (no sudo workaround).

**CLI Wrapper**: Creates `~/.local/bin/pongogo` that runs Docker container.

---

## Release Channels

### Channel Definitions

| Channel | Branch | Tag Pattern | Stability | Audience |
|---------|--------|-------------|-----------|----------|
| Alpha | main | `valpha-*` | Bleeding edge | Internal only |
| Beta | beta | `vbeta-*` | Testing | Dogfooding |
| Stable | stable | `v0.1.0` | Production | External users |

### Promotion Flow

```
main ──(push)──► [auto] ──► vbeta-YYYYMMDD-SHA
                              │
                              ▼
                            beta branch
                              │
                         [manual promote]
                              │
                              ▼
                            v0.1.0
                              │
                              ▼
                         stable branch
```

### Stage0 Bootstrap

For self-development, Pongogo uses a **released beta version** to develop the next version:

```json
// .pongogo-stage0.json
{
  "version": "vbeta-20251220-abc123",
  "updated": "2025-12-20"
}
```

This prevents the platform from shifting during development.

---

## OIDC Authentication

### Why OIDC?

GitHub Actions authenticates to Azure without storing secrets:
- No long-lived credentials
- Automatic token rotation
- Scoped to specific workflows

### Azure AD App Registration

| Property | Value |
|----------|-------|
| App Name | `pongogo-github-actions` |
| Client ID | (in GitHub secrets) |
| Tenant ID | (in GitHub secrets) |

### Federated Identity Credentials

**Traditional Credentials** (exact match only):
| Name | Subject |
|------|---------|
| `pongogo-to-go-main` | `repo:pongogo/pongogo-to-go:ref:refs/heads/main` |
| `pongogo-to-go-beta` | `repo:pongogo/pongogo-to-go:ref:refs/heads/beta` |
| `pongogo-to-go-stable` | `repo:pongogo/pongogo-to-go:ref:refs/heads/stable` |

**Flexible Federated Credential** (wildcard via Graph beta API):

Traditional credentials don't support wildcards. For tag refs (`refs/tags/v*`), we use a **Flexible Federated Identity Credential**:

```json
{
  "name": "pongogo-to-go-all-tags",
  "issuer": "https://token.actions.githubusercontent.com",
  "audiences": ["api://AzureADTokenExchange"],
  "claimsMatchingExpression": {
    "languageVersion": 1,
    "value": "claims['sub'] matches 'repo:pongogo/pongogo-to-go:ref:refs/tags/*'"
  }
}
```

**Why This Works**: The `claimsMatchingExpression` with `languageVersion: 1` allows glob patterns, enabling all tag refs to authenticate.

### GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `AZURE_CLIENT_ID` | Azure AD app client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `CODECOV_TOKEN` | Codecov upload token |

---

## Troubleshooting

### Common Issues

#### Docker Build Failing on Tag Push

**Symptom**: `docker.yml` fails with "OIDC token exchange failed"

**Cause**: Missing federated credential for tag pattern

**Fix**: Verify flexible federated credential exists:
```bash
az rest --method GET \
  --uri "https://graph.microsoft.com/beta/applications/{app-object-id}/federatedIdentityCredentials" \
  | jq '.value[] | select(.name | contains("tags"))'
```

#### Install Script Not Updated

**Symptom**: `curl -sSL https://get.pongogo.com | bash` shows old version

**Cause**: CDN cache not purged

**Fix**: Manually purge CDN:
```bash
az afd endpoint purge \
  --resource-group pongogo-rg \
  --profile-name pongogo-cdn \
  --endpoint-name pongogo-downloads \
  --content-paths "/*"
```

#### Docker Requires Sudo on Linux

**Symptom**: Installer says "Docker requires sudo"

**Cause**: User not in docker group

**Fix**: Add user to docker group:
```bash
sudo usermod -aG docker $USER
newgrp docker  # or log out and back in
```

#### Interactive Prompts Not Working

**Symptom**: Script hangs or skips prompts when run via `curl | bash`

**Cause**: `read` commands reading from stdin (which is the script)

**Fix**: All `read` commands must use `< /dev/tty`

### Debugging Commands

```bash
# Check Azure OIDC
az ad app federated-credential list --id <app-id> -o table

# Check ACR anonymous pull
docker pull pongogo.azurecr.io/pongogo:stable

# Check CDN endpoint
curl -I https://get.pongogo.com

# View CI logs
gh run list --repo pongogo/pongogo-to-go --workflow ci.yml --limit 5

# View Docker build logs
gh run list --repo pongogo/pongogo-to-go --workflow docker.yml --limit 5
```

---

## References

- [Design: CI/CD Workflow Specifications](design/cicd_workflow_specifications.md)
- [Design: Docker Test Environment](design/docker_test_environment.md)
- [Design: Test Pyramid Layers](design/test_pyramid_layers.md)
- [Azure OIDC with GitHub Actions](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure)
- [Flexible Federated Identity Credentials](https://learn.microsoft.com/en-us/graph/api/resources/federatedidentitycredential)
