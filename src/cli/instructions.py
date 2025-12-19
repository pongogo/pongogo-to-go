"""Instruction file management for Pongogo."""

import shutil
from pathlib import Path
from typing import Any

import yaml


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
