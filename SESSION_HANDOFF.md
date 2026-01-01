# Session Handoff: Pongogo Installer & CI/CD Fixes

**Date**: 2026-01-01
**Session Type**: Natural stopping point
**Status**: ✅ COMPLETE

---

## What Was Just Completed

**Work**: Fixed Pongogo installer (get.pongogo.com) and resolved Azure OIDC CI/CD issues for Docker builds

### Install Script Improvements (deploy.yml)
- Fixed gorilla emoji → orangutan emoji 🦧
- Fixed Docker not found message (now shows install instructions before exiting)
- Added Docker start prompt when Docker installed but not running (macOS/Linux)
- Fixed `curl | bash` interactive prompts to read from `/dev/tty`
- Removed automatic pip install (Docker-only installer)
- Added `~/.local/bin/pongogo` CLI wrapper that runs Docker commands
- Added git repo detection with "Would you like to initialize Pongogo here?" prompt
- Changed to require proper docker group setup instead of sudo workaround

### Azure OIDC Fix
- Traditional federated credentials DON'T support wildcards (exact match only)
- Created **Flexible Federated Identity Credential** (preview feature) using Microsoft Graph beta API
- Expression: `claims['sub'] matches 'repo:pongogo/pongogo-to-go:ref:refs/tags/*'`
- All tag refs (including vbeta-*) now authenticate to ACR successfully

**Commits**:
- 9405b35 Revert ACR workaround - using flexible federated credentials for tag wildcards
- c5f6f08 Skip ACR push for beta tags (GHCR only)
- 5be6212 Require proper docker group setup instead of sudo workaround
- 80c81c3 Improve Linux Docker start: try rootless first, better error hints
- 9a3332f Fix interactive prompts to read from /dev/tty for curl|bash
- 4effa26 Offer to start Docker if installed but not running
- c9a02ac Add Docker CLI wrapper with repo detection and init prompt
- a9d2241 Update next steps to Docker-only setup
- 6b925ca Fix Docker install prompt and remove auto pip install

---

## Strategic Decisions Made

### 1. Docker-Only Installation
**Decision**: Remove all pip/pipx auto-install from the installer script

**Rationale**: User wanted clean Docker-only flow. CLI installed via `~/.local/bin/pongogo` wrapper that delegates to Docker.

**Impact**: Users run `pongogo init` which actually runs `docker run ... pongogo init`

### 2. Flexible Federated Identity Credentials
**Decision**: Use Azure's preview "flexible federated identity credentials" feature for wildcard tag matching

**Rationale**: Traditional federated credentials require exact subject match. Wildcards like `refs/tags/*` don't work. Flexible credentials with `claimsMatchingExpression` support glob patterns.

**Impact**: All tag refs now authenticate to ACR. Beta and stable Docker builds push to both GHCR and ACR.

### 3. Proper Docker Group Requirement
**Decision**: Exit with instructions if Docker requires sudo, rather than working around with sudo

**Rationale**: User correctly noted we don't want Pongogo running with sudo. Proper fix is adding user to docker group.

**Impact**: Linux users must be in docker group. Script guides them through setup.

---

## All Changes Committed and Pushed

### Install Script (.github/workflows/deploy.yml)
- Docker detection and start logic
- CLI wrapper creation (`~/.local/bin/pongogo`)
- Git repo detection and init prompt
- Interactive prompts with `/dev/tty`
- Docker group requirement enforcement

### Docker Build (.github/workflows/docker.yml)
- Briefly had ACR skip for beta tags (workaround)
- Reverted to push all tags to both GHCR and ACR

### Azure Infrastructure
- Deleted non-working wildcard credentials (pongogo-to-go-tags, pongogo-to-go-beta-tags)
- Created flexible federated identity credential via Graph beta API

---

## Current Status

**Installer**: ✅ Working at https://get.pongogo.com
**CI/CD**: ✅ Docker builds for main and all tags push to GHCR + ACR
**User Testing**: Tested on Fedora (docker group issues identified and resolved)

---

## What's Next

### Immediate Next Step
**User Testing**: User should test the installer end-to-end:
```bash
curl -sSL https://get.pongogo.com | bash
```

### Expected Flow
1. Checks Docker installed
2. Offers to start Docker if not running
3. If Docker needs sudo → guides user to add to docker group
4. Pulls pongogo image from ACR
5. Configures Claude Code MCP server
6. Creates ~/.local/bin/pongogo wrapper
7. If in git repo → offers to run `pongogo init`

### How to Begin Next Session
1. Test installer on clean environment
2. Verify `pongogo init` creates .pongogo directory correctly
3. Test MCP server integration with Claude Code

---

## Context for Resumption

### Why We Paused
- Natural stopping point - all fixes deployed and verified
- CI/CD working, installer updated

### Session Characteristics
- **Duration**: Extended session (~2-3 hours)
- **Work Type**: Infrastructure / DevOps / CI/CD
- **Key Pattern**: Iterative fix-deploy-test cycles with user feedback
- **Quality**: High - all issues resolved systematically

### Important Files Modified
- `.github/workflows/deploy.yml` - Main install script
- `.github/workflows/docker.yml` - Docker build workflow
- Azure AD: Flexible federated identity credential created

---

## Key Learnings This Session

1. **Flexible Federated Credentials**: Azure AD traditional federated credentials don't support wildcards. Must use preview "flexible federated identity credentials" with `claimsMatchingExpression` and `languageVersion: 1`.

2. **curl | bash Interactive Prompts**: `read` commands in piped scripts must read from `/dev/tty` not stdin (which is the script content).

3. **Docker Group vs Sudo**: Proper approach is requiring docker group membership, not sudo workarounds.

---

## Quick Reference

### Test Installer
```bash
curl -sSL https://get.pongogo.com | bash
```

### Check CI/CD
```bash
gh run list --repo pongogo/pongogo-to-go --workflow docker.yml --limit 5
```

### Azure Federated Credentials
```bash
az ad app federated-credential list --id 159bfccd-7588-469f-93a5-6f517ae7458c -o table
```

---

## Handoff Validation

- ✅ All commits pushed to main
- ✅ Deploy workflow completed successfully
- ✅ Docker builds (main + beta tags) succeeding
- ✅ Azure OIDC working for all tag refs
- ✅ Install script deployed to get.pongogo.com

**Ready for Pickup**: Session complete. User can test installer or continue with P05 work.

---

**Generated**: 2026-01-01 12:38 EST
**Next Work**: User testing of installer flow
