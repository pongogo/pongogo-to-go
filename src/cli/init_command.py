"""The pongogo init command implementation."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from .config import generate_config, write_config
from .instructions import (
    copy_instructions,
    copy_manifest,
    get_enabled_categories,
    get_package_instructions_dir,
    load_manifest,
)


# Import discovery system (lazy import to avoid circular dependencies)
def get_discovery_system():
    """Lazy import of DiscoverySystem to avoid circular imports."""
    import sys
    from pathlib import Path

    # Add mcp-server to path if needed
    mcp_server_path = Path(__file__).parent.parent / "mcp-server"
    if str(mcp_server_path) not in sys.path:
        sys.path.insert(0, str(mcp_server_path))
    from discovery_system import DiscoverySystem

    return DiscoverySystem


console = Console()

PONGOGO_DIR = ".pongogo"
CONFIG_FILE = "config.yaml"
INSTRUCTIONS_DIR = "instructions"

# Common wiki/docs folder names to detect
WIKI_FOLDER_NAMES = ["wiki", "Wiki", ".wiki"]
DOCS_FOLDER_NAMES = ["docs", "Docs", "documentation", "Documentation"]


def detect_knowledge_folders(cwd: Path) -> tuple[Path | None, Path | None]:
    """Detect existing wiki and docs folders in the project.

    Returns:
        Tuple of (wiki_path, docs_path) - each is None if not found.
    """
    wiki_path = None
    docs_path = None

    for name in WIKI_FOLDER_NAMES:
        candidate = cwd / name
        if candidate.is_dir():
            wiki_path = candidate
            break

    for name in DOCS_FOLDER_NAMES:
        candidate = cwd / name
        if candidate.is_dir():
            docs_path = candidate
            break

    return wiki_path, docs_path


def offer_knowledge_folder_creation(
    cwd: Path,
    wiki_path: Path | None,
    docs_path: Path | None,
    no_interactive: bool,
) -> tuple[Path | None, Path | None]:
    """Offer to create wiki/docs folders with reassurance-first messaging.

    Philosophy: "red x's are scary" - always show the solution alongside any finding.
    Never show problems without solutions. Use reassurance-first approach.

    Returns:
        Tuple of (created_wiki_path, created_docs_path)
    """
    created_wiki = None
    created_docs = None

    # Check what's missing
    missing_wiki = wiki_path is None
    missing_docs = docs_path is None

    if not missing_wiki and not missing_docs:
        # Both exist, nothing to offer
        return None, None

    # Reassurance-first messaging - show the solution with the finding
    console.print()
    console.print(
        Panel(
            "[bold green]Knowledge Folders[/bold green]\n\n"
            "Pongogo works best when your project has dedicated folders for "
            "institutional knowledge - this helps AI agents understand your project's "
            "architecture and decisions.\n\n"
            "[dim]This isn't a problem if you don't have them yet - "
            "we can create them for you![/dim]",
            title="Checking Project Structure",
            border_style="blue",
        )
    )

    # Report what was found with positive framing
    if not missing_wiki:
        console.print(f"  [green]Found[/green] wiki folder: {wiki_path.name}/")
    if not missing_docs:
        console.print(f"  [green]Found[/green] docs folder: {docs_path.name}/")

    # Offer to create missing folders with reassurance
    if missing_wiki:
        console.print("  [dim]No wiki folder found - that's totally fine![/dim]")

        if no_interactive:
            # Non-interactive: create by default
            created_wiki = cwd / "wiki"
            created_wiki.mkdir(exist_ok=True)
            console.print("  [green]Created[/green] wiki/ folder")
        else:
            # Interactive: ask with positive framing
            create_wiki = Confirm.ask(
                "  Would you like to create a [bold]wiki/[/bold] folder for project documentation?",
                default=True,
            )
            if create_wiki:
                created_wiki = cwd / "wiki"
                created_wiki.mkdir(exist_ok=True)
                console.print("  [green]Created[/green] wiki/ folder")

                # Create a starter file to help users
                readme = created_wiki / "Home.md"
                if not readme.exists():
                    readme.write_text(
                        "# Project Wiki\n\n"
                        "Welcome to your project wiki! This folder is for:\n\n"
                        "- **Architecture decisions** - Why things are built the way they are\n"
                        "- **Strategic context** - High-level project direction\n"
                        "- **Onboarding guides** - Help new contributors get started\n\n"
                        "## Getting Started\n\n"
                        "If you're using GitHub, this folder can sync with your repository's wiki.\n"
                        "See: https://docs.github.com/en/communities/documenting-your-project-with-wikis\n"
                    )
                    console.print("  [green]Created[/green] wiki/Home.md starter file")

    if missing_docs:
        console.print("  [dim]No docs folder found - no worries![/dim]")

        if no_interactive:
            # Non-interactive: create by default
            created_docs = cwd / "docs"
            created_docs.mkdir(exist_ok=True)
            console.print("  [green]Created[/green] docs/ folder")
        else:
            # Interactive: ask with positive framing
            create_docs = Confirm.ask(
                "  Would you like to create a [bold]docs/[/bold] folder for technical documentation?",
                default=True,
            )
            if create_docs:
                created_docs = cwd / "docs"
                created_docs.mkdir(exist_ok=True)
                console.print("  [green]Created[/green] docs/ folder")

                # Create a starter README
                readme = created_docs / "README.md"
                if not readme.exists():
                    readme.write_text(
                        "# Documentation\n\n"
                        "This folder contains technical documentation for the project:\n\n"
                        "- **API references** - How to use project APIs\n"
                        "- **Setup guides** - Installation and configuration\n"
                        "- **Architecture docs** - Technical design documents\n\n"
                        "## Organization\n\n"
                        "Consider organizing your docs by audience:\n"
                        "- `guides/` - How-to guides for common tasks\n"
                        "- `reference/` - API and configuration reference\n"
                        "- `architecture/` - Design decisions and diagrams\n"
                    )
                    console.print(
                        "  [green]Created[/green] docs/README.md starter file"
                    )

    return created_wiki, created_docs


def init_command(
    minimal: bool = typer.Option(
        False,
        "--minimal",
        "-m",
        help="Only install core instruction categories (software_engineering, safety_prevention)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing .pongogo directory",
    ),
    no_interactive: bool = typer.Option(
        False,
        "--no-interactive",
        "-y",
        help="Accept all defaults without prompting",
    ),
) -> None:
    """Initialize Pongogo in the current directory.

    Creates a .pongogo/ directory with configuration and seeded instruction files.
    """
    cwd = Path.cwd()
    pongogo_dir = cwd / PONGOGO_DIR

    # Check for existing installation
    if pongogo_dir.exists():
        if not force:
            console.print(
                f"[red]Error:[/red] {PONGOGO_DIR}/ already exists. "
                "Use --force to overwrite.",
                style="bold",
            )
            raise typer.Exit(1)
        else:
            console.print(
                f"[yellow]Overwriting existing {PONGOGO_DIR}/ directory...[/yellow]"
            )
            import shutil

            shutil.rmtree(pongogo_dir)

    # Show welcome message
    console.print(
        Panel(
            "[bold blue]Pongogo[/bold blue] - AI agent knowledge routing\n\n"
            "This will create a .pongogo/ directory with:\n"
            "  - config.yaml (configuration)\n"
            "  - instructions/ (seeded instruction files)",
            title="Initializing Pongogo",
            border_style="blue",
        )
    )

    # Interactive mode: prompt for options
    if not no_interactive and not minimal:
        minimal = typer.confirm(
            "Use minimal installation (core instructions only)?",
            default=False,
        )

    # Check for wiki/docs folders and offer to create them
    # Philosophy: "red x's are scary" - show solutions alongside findings
    wiki_path, docs_path = detect_knowledge_folders(cwd)
    created_wiki, created_docs = offer_knowledge_folder_creation(
        cwd, wiki_path, docs_path, no_interactive
    )

    # Track created folders for config
    final_wiki = created_wiki or wiki_path
    final_docs = created_docs or docs_path

    # Generate configuration with detected/created paths
    console.print("\n[bold]Creating configuration...[/bold]")
    config = generate_config(
        minimal=minimal,
        wiki_path=f"{final_wiki.name}/" if final_wiki else None,
        docs_path=f"{final_docs.name}/" if final_docs else None,
    )

    config_path = pongogo_dir / CONFIG_FILE
    write_config(config_path, config)
    console.print(f"  [green]Created[/green] {PONGOGO_DIR}/{CONFIG_FILE}")

    # Copy instruction files
    console.print("\n[bold]Copying instruction files...[/bold]")

    try:
        source_dir = get_package_instructions_dir()
        manifest = load_manifest(source_dir)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    dest_instructions_dir = pongogo_dir / INSTRUCTIONS_DIR
    enabled_categories = get_enabled_categories(manifest, config["categories"])

    files_copied = copy_instructions(
        source_dir=source_dir,
        dest_dir=dest_instructions_dir,
        manifest=manifest,
        enabled_categories=enabled_categories,
    )

    # Copy manifest
    copy_manifest(source_dir, dest_instructions_dir)

    console.print(f"  [green]Copied[/green] {files_copied} instruction files")
    console.print(f"  [green]Categories:[/green] {', '.join(enabled_categories)}")

    # Scan repository for existing knowledge patterns
    console.print("\n[bold]Discovering repository knowledge...[/bold]")
    discovery_summary = None
    try:
        DiscoverySystem = get_discovery_system()
        ds = DiscoverySystem(cwd)
        scan_result = ds.scan_repository()
        discovery_summary = ds.format_scan_summary(scan_result)
        console.print(discovery_summary)
    except Exception as e:
        console.print(f"  [yellow]Warning:[/yellow] Discovery scan failed: {e}")
        console.print("  [dim]You can run 'pongogo discoveries rescan' later[/dim]")

    # Build success message with created folders
    created_items = [
        f"  - {CONFIG_FILE}",
        f"  - {INSTRUCTIONS_DIR}/ ({files_copied} files)",
    ]
    if created_wiki:
        created_items.append("  - wiki/ (new)")
    if created_docs:
        created_items.append("  - docs/ (new)")

    # Success message
    console.print(
        Panel(
            f"[green]Pongogo initialized successfully![/green]\n\n"
            f"Created: {PONGOGO_DIR}/\n" + "\n".join(created_items) + "\n\n"
            "[dim]Next steps:[/dim]\n"
            "  1. Review and customize .pongogo/config.yaml\n"
            "  2. Configure MCP server for Claude Code integration\n"
            "  3. See https://github.com/pongogo/pongogo-to-go for documentation",
            title="Success",
            border_style="green",
        )
    )
