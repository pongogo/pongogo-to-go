"""Discovery CLI commands for managing repository knowledge discoveries."""

from pathlib import Path

import typer

from .console import console, create_table, print_panel, print_table


# Lazy import to avoid circular dependencies
def get_discovery_system():
    """Lazy import of DiscoverySystem."""
    import sys

    mcp_server_path = Path(__file__).parent.parent / "mcp-server"
    if str(mcp_server_path) not in sys.path:
        sys.path.insert(0, str(mcp_server_path))
    from discovery_system import DiscoverySystem

    return DiscoverySystem


app = typer.Typer(
    name="discoveries",
    help="Manage repository knowledge discoveries",
    no_args_is_help=True,
)


def _get_project_root() -> Path:
    """Find project root by looking for .pongogo directory."""
    cwd = Path.cwd()
    # Check current directory and parents
    for path in [cwd] + list(cwd.parents):
        if (path / ".pongogo").is_dir():
            return path
    return cwd


def _ensure_discovery_system():
    """Get DiscoverySystem instance, or None if not available."""
    project_root = _get_project_root()
    pongogo_dir = project_root / ".pongogo"

    if not pongogo_dir.exists():
        console.print(
            "[red]Error:[/red] No .pongogo directory found. "
            "Run 'pongogo init' first.",
            style="bold",
        )
        raise typer.Exit(1)

    DiscoverySystem = get_discovery_system()
    return DiscoverySystem(project_root)


@app.command(name="list")
def list_discoveries(
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status: DISCOVERED, PROMOTED, or ARCHIVED",
    ),
    source_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by source type: CLAUDE_MD, WIKI, or DOCS",
    ),
    limit: int = typer.Option(
        50,
        "--limit",
        "-n",
        help="Maximum number of discoveries to show",
    ),
) -> None:
    """List all discoveries in the repository.

    Shows discovered knowledge patterns from CLAUDE.md, wiki/, and docs/.
    """
    ds = _ensure_discovery_system()

    discoveries = ds.list_discoveries(
        status=status,
        source_type=source_type,
        limit=limit,
    )

    if not discoveries:
        console.print("[dim]No discoveries found.[/dim]")
        if status or source_type:
            console.print("[dim]Try removing filters to see all discoveries.[/dim]")
        return

    # Create table
    table = create_table("Repository Knowledge Discoveries")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Status", style="magenta")
    table.add_column("Type", style="blue")
    table.add_column("Title", style="green")
    table.add_column("Source", style="dim")

    for d in discoveries:
        status_style = {
            "DISCOVERED": "[yellow]DISCOVERED[/yellow]",
            "PROMOTED": "[green]PROMOTED[/green]",
            "ARCHIVED": "[dim]ARCHIVED[/dim]",
        }.get(d.status, d.status)

        title = d.section_title or "(no title)"
        if len(title) > 40:
            title = title[:37] + "..."

        source = d.source_file
        if len(source) > 30:
            source = "..." + source[-27:]

        table.add_row(
            str(d.id),
            status_style,
            d.source_type,
            title,
            source,
        )

    print_table(table)

    # Show stats
    stats = ds.get_stats()
    console.print(
        f"\n[dim]Total: {stats['total']} | "
        f"Discovered: {stats['by_status'].get('DISCOVERED', 0)} | "
        f"Promoted: {stats['by_status'].get('PROMOTED', 0)} | "
        f"Archived: {stats['by_status'].get('ARCHIVED', 0)}[/dim]"
    )


@app.command(name="show")
def show_discovery(
    discovery_id: int = typer.Argument(..., help="ID of the discovery to show"),
) -> None:
    """Show details of a specific discovery.

    Displays full content, keywords, and metadata.
    """
    ds = _ensure_discovery_system()

    discovery = ds.get_discovery(discovery_id)
    if not discovery:
        console.print(f"[red]Error:[/red] Discovery #{discovery_id} not found.")
        raise typer.Exit(1)

    # Build content panel
    content_lines = [
        f"[bold]Status:[/bold] {discovery.status}",
        f"[bold]Source Type:[/bold] {discovery.source_type}",
        f"[bold]Source File:[/bold] {discovery.source_file}",
        f"[bold]Discovered:[/bold] {discovery.discovered_at}",
    ]

    if discovery.promoted_at:
        content_lines.append(f"[bold]Promoted:[/bold] {discovery.promoted_at}")
    if discovery.instruction_file:
        content_lines.append(f"[bold]Instruction:[/bold] {discovery.instruction_file}")
    if discovery.archived_at:
        content_lines.append(f"[bold]Archived:[/bold] {discovery.archived_at}")
        content_lines.append(f"[bold]Archive Reason:[/bold] {discovery.archive_reason}")

    if discovery.keywords:
        keywords = ", ".join(discovery.keywords[:15])
        if len(discovery.keywords) > 15:
            keywords += f" (+{len(discovery.keywords) - 15} more)"
        content_lines.append(f"[bold]Keywords:[/bold] {keywords}")

    content_lines.append("")
    content_lines.append("[bold]Content:[/bold]")
    content_lines.append("─" * 60)

    # Truncate very long content
    content = discovery.section_content
    if len(content) > 2000:
        content = (
            content[:2000] + "\n\n[dim]... (truncated, showing first 2000 chars)[/dim]"
        )
    content_lines.append(content)

    title = discovery.section_title or "(Untitled Section)"
    print_panel(
        f"Discovery #{discovery.id}: {title}",
        "\n".join(content_lines),
        style="blue",
    )


@app.command(name="promote")
def promote_discovery(
    discovery_id: int = typer.Argument(..., help="ID of the discovery to promote"),
) -> None:
    """Manually promote a discovery to an instruction file.

    Creates an instruction file in .pongogo/instructions/_discovered/
    """
    ds = _ensure_discovery_system()

    discovery = ds.get_discovery(discovery_id)
    if not discovery:
        console.print(f"[red]Error:[/red] Discovery #{discovery_id} not found.")
        raise typer.Exit(1)

    if discovery.status == "PROMOTED":
        console.print(
            f"[yellow]Warning:[/yellow] Discovery #{discovery_id} is already promoted."
        )
        console.print(f"[dim]Instruction file: {discovery.instruction_file}[/dim]")
        return

    if discovery.status == "ARCHIVED":
        console.print(
            "[red]Error:[/red] Cannot promote archived discovery. "
            "Unarchive it first."
        )
        raise typer.Exit(1)

    # Promote
    instruction_path = ds.promote(discovery_id)
    if instruction_path:
        console.print(
            f"[green]Promoted[/green] Discovery #{discovery_id} → {instruction_path}"
        )
    else:
        console.print("[red]Error:[/red] Failed to promote discovery.")
        raise typer.Exit(1)


@app.command(name="archive")
def archive_discovery(
    discovery_id: int = typer.Argument(..., help="ID of the discovery to archive"),
    reason: str = typer.Option(
        "Marked as not useful",
        "--reason",
        "-r",
        help="Reason for archiving",
    ),
) -> None:
    """Archive a discovery (mark as not useful).

    Archived discoveries won't be considered for promotion.
    """
    ds = _ensure_discovery_system()

    discovery = ds.get_discovery(discovery_id)
    if not discovery:
        console.print(f"[red]Error:[/red] Discovery #{discovery_id} not found.")
        raise typer.Exit(1)

    if discovery.status == "ARCHIVED":
        console.print(
            f"[yellow]Warning:[/yellow] Discovery #{discovery_id} is already archived."
        )
        return

    # Archive
    if ds.archive_discovery(discovery_id, reason):
        console.print(f"[green]Archived[/green] Discovery #{discovery_id}: {reason}")
    else:
        console.print("[red]Error:[/red] Failed to archive discovery.")
        raise typer.Exit(1)


@app.command(name="rescan")
def rescan_repository() -> None:
    """Re-scan repository for knowledge patterns.

    Scans CLAUDE.md, wiki/, and docs/ for new or updated content.
    """
    project_root = _get_project_root()
    pongogo_dir = project_root / ".pongogo"

    if not pongogo_dir.exists():
        console.print(
            "[red]Error:[/red] No .pongogo directory found. "
            "Run 'pongogo init' first.",
            style="bold",
        )
        raise typer.Exit(1)

    console.print("[bold]Re-scanning repository for knowledge patterns...[/bold]")

    DiscoverySystem = get_discovery_system()
    ds = DiscoverySystem(project_root)

    scan_result = ds.scan_repository()
    summary = ds.format_scan_summary(scan_result)
    console.print(summary)

    if scan_result.new_discoveries > 0:
        console.print(
            f"\n[green]Added {scan_result.new_discoveries} new discoveries.[/green]"
        )
    if scan_result.updated_discoveries > 0:
        console.print(
            f"[dim]Updated {scan_result.updated_discoveries} existing discoveries.[/dim]"
        )


@app.command(name="stats")
def show_stats() -> None:
    """Show discovery system statistics.

    Displays counts by status and source type.
    """
    ds = _ensure_discovery_system()
    stats = ds.get_stats()

    content = (
        f"Total Discoveries: {stats['total']}\n\n"
        f"By Status:\n"
        f"  Discovered: {stats['by_status'].get('DISCOVERED', 0)}\n"
        f"  Promoted: {stats['by_status'].get('PROMOTED', 0)}\n"
        f"  Archived: {stats['by_status'].get('ARCHIVED', 0)}\n\n"
        f"By Source:\n"
        f"  CLAUDE.md: {stats['by_source'].get('CLAUDE_MD', 0)}\n"
        f"  Wiki: {stats['by_source'].get('WIKI', 0)}\n"
        f"  Docs: {stats['by_source'].get('DOCS', 0)}"
    )
    print_panel("Discovery System Statistics", content, style="blue")
