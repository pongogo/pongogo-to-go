---
description: Upgrade Pongogo to latest version
---

# Pongogo Upgrade

Upgrade Pongogo to the latest version.

## Usage

```
/pongogo-upgrade
```

## Execution

**Execute the upgrade command and display the result.**

Run the following Bash command:

```bash
pongogo upgrade
```

This command:
1. Pulls the latest Docker image from the registry
2. Shows upgrade progress
3. Instructs user to restart Claude Code

## Output

The `pongogo upgrade` command will output:

- Progress indicator ("Upgrading Pongogo...")
- Success message with restart instructions
- Or error message if upgrade fails

## After Upgrade

After the upgrade completes, tell the user:

```
Upgrade complete! To use the new version:
1. Exit Claude Code
2. Re-enter Claude Code
3. Run /mcp to verify Pongogo is connected
```
