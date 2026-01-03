"""Instruction file management for Pongogo."""

import shutil
from pathlib import Path
from typing import Any

import yaml

# Protected instruction names that cannot be overridden by user files
# These correspond to core instructions bundled with the package
PROTECTED_NAMES = frozenset(
    {
        "collaboration",
        "incident_handling",
        "issue_closure",
        "issue_creation",
        "issue_status",
        "learning_loop",
        "pi_tracking",
        "planning",
        "work_logging",
    }
)

# Category that contains protected core instructions (bundled, not copied)
CORE_CATEGORY = "_pongogo_core"


def get_package_instructions_dir() -> Path:
    """Get the path to bundled instructions directory.

    Returns:
        Path to instructions directory within the package
    """
    # Instructions are bundled at the package root level
    package_root = Path(__file__).parent.parent.parent
    instructions_dir = package_root / "instructions"

    if not instructions_dir.exists():
        raise FileNotFoundError(
            f"Instructions directory not found at {instructions_dir}. "
            "This may indicate a packaging issue."
        )

    return instructions_dir


def load_manifest(instructions_dir: Path) -> dict[str, Any]:
    """Load the instructions manifest.

    Args:
        instructions_dir: Path to instructions directory

    Returns:
        Manifest dictionary
    """
    manifest_path = instructions_dir / "manifest.yaml"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    with open(manifest_path) as f:
        return yaml.safe_load(f)


def get_enabled_categories(
    manifest: dict[str, Any],
    config_categories: dict[str, bool],
) -> list[str]:
    """Get list of categories to copy based on config.

    Args:
        manifest: The instructions manifest
        config_categories: Category enable/disable settings from config

    Returns:
        List of enabled category names
    """
    enabled = []

    for category_name in manifest.get("categories", {}):
        if config_categories.get(category_name, True):
            enabled.append(category_name)

    return enabled


def copy_instructions(
    source_dir: Path,
    dest_dir: Path,
    manifest: dict[str, Any],
    enabled_categories: list[str],
) -> int:
    """Copy instruction files for enabled categories.

    Note: Core instructions (_pongogo_core) are NOT copied - they remain
    bundled in the package and are loaded separately by the MCP server.

    Args:
        source_dir: Source instructions directory
        dest_dir: Destination .pongogo/instructions directory
        manifest: The instructions manifest
        enabled_categories: List of category names to copy

    Returns:
        Number of files copied
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    files_copied = 0
    categories = manifest.get("categories", {})

    for category_name in enabled_categories:
        # Skip core instructions - they're bundled, not copied
        if category_name == CORE_CATEGORY:
            continue

        category = categories.get(category_name, {})
        files = category.get("files", [])

        for file_info in files:
            file_path = file_info.get("path", "")
            if not file_path:
                continue

            source_file = source_dir / file_path
            dest_file = dest_dir / file_path

            if source_file.exists():
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, dest_file)
                files_copied += 1

    return files_copied


def get_core_instructions_path() -> Path | None:
    """Get path to package-bundled core instructions.

    Core instructions are protected and always available, even if user
    deletes their .pongogo/instructions directory.

    Returns:
        Path to _pongogo_core directory, or None if not found
    """
    try:
        package_instructions = get_package_instructions_dir()
        core_path = package_instructions / CORE_CATEGORY
        return core_path if core_path.exists() else None
    except FileNotFoundError:
        return None


def is_protected_name(name: str) -> bool:
    """Check if an instruction name is protected.

    Args:
        name: Instruction file name (without .instructions.md extension)

    Returns:
        True if name is protected and cannot be overridden
    """
    # Strip common prefixes and extensions
    clean_name = name.replace("core:", "").replace(".instructions.md", "")
    clean_name = clean_name.replace("_pongogo_", "")
    return clean_name in PROTECTED_NAMES


def copy_manifest(source_dir: Path, dest_dir: Path) -> None:
    """Copy manifest file to destination.

    Args:
        source_dir: Source instructions directory
        dest_dir: Destination instructions directory
    """
    source_manifest = source_dir / "manifest.yaml"
    dest_manifest = dest_dir / "manifest.yaml"

    if source_manifest.exists():
        shutil.copy2(source_manifest, dest_manifest)


def get_package_commands_dir() -> Path | None:
    """Get the path to bundled slash commands directory.

    Returns:
        Path to .claude/commands directory within the package, or None if not found
    """
    package_root = Path(__file__).parent.parent.parent
    commands_dir = package_root / ".claude" / "commands"

    return commands_dir if commands_dir.exists() else None


def copy_slash_commands(dest_dir: Path) -> int:
    """Copy slash commands to user's .claude/commands directory.

    Args:
        dest_dir: Destination .claude/commands directory

    Returns:
        Number of command files copied
    """
    source_dir = get_package_commands_dir()
    if source_dir is None:
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)

    files_copied = 0
    for source_file in source_dir.glob("*.md"):
        dest_file = dest_dir / source_file.name
        shutil.copy2(source_file, dest_file)
        files_copied += 1

    return files_copied
