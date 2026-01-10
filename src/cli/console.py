"""Console output utilities with graceful degradation.

Provides rich-like output when rich is available, falls back to plain
print statements when it's not. This enables the CLI to work on systems
where rich isn't installed (e.g., Fedora without pip).

Usage:
    from cli.console import console, print_panel, print_success, print_error

    console.print("Hello world", style="bold")
    print_success("Operation completed")
    print_error("Something went wrong")
    print_panel("Title", "Content here")
"""

from typing import Any

# Try to import rich, gracefully degrade if not available
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None  # type: ignore
    Panel = None  # type: ignore
    Table = None  # type: ignore


class PlainConsole:
    """Fallback console that uses plain print statements."""

    def print(self, *args: Any, style: str = "", **kwargs: Any) -> None:
        """Print with optional style (ignored in plain mode)."""
        # Filter out rich-specific kwargs
        plain_kwargs = {
            k: v for k, v in kwargs.items() if k in ("end", "file", "flush")
        }
        print(*args, **plain_kwargs)

    def rule(self, title: str = "", style: str = "") -> None:
        """Print a horizontal rule."""
        if title:
            print(f"\n{'=' * 20} {title} {'=' * 20}\n")
        else:
            print("=" * 60)


# Use rich console if available, otherwise plain
if not RICH_AVAILABLE:
    console = PlainConsole()  # type: ignore


def print_success(message: str) -> None:
    """Print a success message (green checkmark)."""
    if RICH_AVAILABLE:
        console.print(f"[green]✓[/green] {message}")
    else:
        print(f"✓ {message}")


def print_error(message: str) -> None:
    """Print an error message (red X)."""
    if RICH_AVAILABLE:
        console.print(f"[red]✗[/red] {message}")
    else:
        print(f"✗ {message}")


def print_warning(message: str) -> None:
    """Print a warning message (yellow warning sign)."""
    if RICH_AVAILABLE:
        console.print(f"[yellow]⚠[/yellow] {message}")
    else:
        print(f"⚠ {message}")


def print_info(message: str) -> None:
    """Print an info message (blue info sign)."""
    if RICH_AVAILABLE:
        console.print(f"[blue]ℹ[/blue] {message}")
    else:
        print(f"ℹ {message}")


def print_panel(title: str, content: str, style: str = "blue") -> None:
    """Print content in a panel/box."""
    if RICH_AVAILABLE and Panel:
        console.print(Panel(content, title=title, border_style=style))
    else:
        width = max(len(title) + 4, max(len(line) for line in content.split("\n")) + 4)
        print("┌" + "─" * (width - 2) + "┐")
        print(f"│ {title}{' ' * (width - len(title) - 4)} │")
        print("├" + "─" * (width - 2) + "┤")
        for line in content.split("\n"):
            padding = width - len(line) - 4
            print(f"│ {line}{' ' * padding} │")
        print("└" + "─" * (width - 2) + "┘")


def create_table(title: str = "") -> Any:
    """Create a table object (rich Table or plain dict collector)."""
    if RICH_AVAILABLE and Table:
        return Table(title=title) if title else Table()
    else:
        return PlainTable(title)


class PlainTable:
    """Fallback table that collects data and prints as plain text."""

    def __init__(self, title: str = ""):
        self.title = title
        self.columns: list[str] = []
        self.rows: list[list[str]] = []

    def add_column(self, name: str, **kwargs: Any) -> None:
        """Add a column header."""
        self.columns.append(name)

    def add_row(self, *values: str) -> None:
        """Add a row of values."""
        self.rows.append(list(values))

    def __str__(self) -> str:
        """Render table as plain text."""
        if not self.columns:
            return ""

        # Calculate column widths
        widths = [len(col) for col in self.columns]
        for row in self.rows:
            for i, val in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(str(val)))

        # Build output
        lines = []
        if self.title:
            lines.append(self.title)
            lines.append("-" * len(self.title))

        # Header
        header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(self.columns))
        lines.append(header)
        lines.append("-" * len(header))

        # Rows
        for row in self.rows:
            row_str = " | ".join(
                str(val).ljust(widths[i]) if i < len(widths) else str(val)
                for i, val in enumerate(row)
            )
            lines.append(row_str)

        return "\n".join(lines)


def print_table(table: Any) -> None:
    """Print a table (rich or plain)."""
    if RICH_AVAILABLE:
        console.print(table)
    else:
        print(str(table))


# Re-export for convenience
__all__ = [
    "RICH_AVAILABLE",
    "console",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "print_panel",
    "create_table",
    "print_table",
    "PlainTable",
]
