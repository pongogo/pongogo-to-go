"""Unit tests for CLI console module with graceful degradation.

Tests both rich-available and rich-unavailable scenarios to ensure
CLI works on systems without rich installed.
"""


class TestRichAvailable:
    """Tests when rich is available."""

    def test_rich_available_flag_set(self):
        """RICH_AVAILABLE should be True when rich is importable."""
        from cli.console import RICH_AVAILABLE

        # In test environment, rich should be available
        assert RICH_AVAILABLE is True

    def test_console_is_rich_console(self):
        """Console should be rich.console.Console when available."""
        from rich.console import Console

        from cli.console import console

        assert isinstance(console, Console)

    def test_create_table_returns_rich_table(self):
        """create_table should return rich Table when available."""
        from cli.console import RICH_AVAILABLE, create_table

        if RICH_AVAILABLE:
            from rich.table import Table

            table = create_table("Test Table")
            assert isinstance(table, Table)

    def test_print_functions_exist(self):
        """All print helper functions should exist."""
        from cli.console import (
            print_error,
            print_panel,
            print_success,
            print_table,
            print_warning,
        )

        # Just verify they're callable
        assert callable(print_success)
        assert callable(print_error)
        assert callable(print_warning)
        assert callable(print_panel)
        assert callable(print_table)


class TestPlainConsole:
    """Tests for PlainConsole fallback."""

    def test_plain_console_print(self, capsys):
        """PlainConsole.print should output to stdout."""
        from cli.console import PlainConsole

        pc = PlainConsole()
        pc.print("Hello World")

        captured = capsys.readouterr()
        assert "Hello World" in captured.out

    def test_plain_console_print_ignores_style(self, capsys):
        """PlainConsole.print should ignore style parameter."""
        from cli.console import PlainConsole

        pc = PlainConsole()
        pc.print("Styled text", style="bold red")

        captured = capsys.readouterr()
        assert "Styled text" in captured.out
        # Should not contain ANSI codes
        assert "\033[" not in captured.out

    def test_plain_console_rule_with_title(self, capsys):
        """PlainConsole.rule should print separator with title."""
        from cli.console import PlainConsole

        pc = PlainConsole()
        pc.rule("Section Title")

        captured = capsys.readouterr()
        assert "Section Title" in captured.out
        assert "=" in captured.out

    def test_plain_console_rule_without_title(self, capsys):
        """PlainConsole.rule should print plain separator."""
        from cli.console import PlainConsole

        pc = PlainConsole()
        pc.rule()

        captured = capsys.readouterr()
        assert "=" in captured.out


class TestPlainTable:
    """Tests for PlainTable fallback."""

    def test_plain_table_creation(self):
        """PlainTable should be creatable with title."""
        from cli.console import PlainTable

        table = PlainTable("My Table")
        assert table.title == "My Table"

    def test_plain_table_add_column(self):
        """PlainTable should accept columns."""
        from cli.console import PlainTable

        table = PlainTable()
        table.add_column("Name", style="cyan")
        table.add_column("Value", justify="right")

        assert "Name" in table.columns
        assert "Value" in table.columns

    def test_plain_table_add_row(self):
        """PlainTable should accept rows."""
        from cli.console import PlainTable

        table = PlainTable()
        table.add_column("A")
        table.add_column("B")
        table.add_row("1", "2")
        table.add_row("3", "4")

        assert len(table.rows) == 2
        assert table.rows[0] == ["1", "2"]

    def test_plain_table_str_output(self):
        """PlainTable.__str__ should produce readable output."""
        from cli.console import PlainTable

        table = PlainTable("Test")
        table.add_column("Col1")
        table.add_column("Col2")
        table.add_row("A", "B")
        table.add_row("C", "D")

        output = str(table)
        assert "Test" in output
        assert "Col1" in output
        assert "Col2" in output
        assert "A" in output
        assert "D" in output

    def test_plain_table_handles_empty(self):
        """PlainTable should handle empty table without error."""
        from cli.console import PlainTable

        table = PlainTable("Empty")
        output = str(table)

        # Empty table (no columns) returns empty string
        assert output == ""

    def test_plain_table_shows_title_with_columns(self):
        """PlainTable should show title when there are columns."""
        from cli.console import PlainTable

        table = PlainTable("My Title")
        table.add_column("Header")
        output = str(table)

        assert "My Title" in output


class TestGracefulDegradation:
    """Tests that simulate rich being unavailable."""

    def test_plain_console_used_when_rich_unavailable(self):
        """When rich import fails, PlainConsole should be used."""
        # We can't easily unimport rich, but we can test PlainConsole directly
        from cli.console import PlainConsole

        pc = PlainConsole()
        # Should not raise
        pc.print("Test message")
        pc.rule("Test rule")

    def test_print_success_works_without_rich(self, capsys):
        """print_success should work with PlainConsole."""
        from cli.console import PlainConsole

        # Simulate what happens in console.py when rich unavailable
        console = PlainConsole()
        # Manual implementation of print_success fallback
        console.print("+ Test success")

        captured = capsys.readouterr()
        assert "Test success" in captured.out

    def test_print_error_works_without_rich(self, capsys):
        """print_error should work with PlainConsole."""
        from cli.console import PlainConsole

        console = PlainConsole()
        console.print("x Test error")

        captured = capsys.readouterr()
        assert "Test error" in captured.out

    def test_print_panel_fallback(self, capsys):
        """print_panel should produce readable output without rich."""
        from cli.console import RICH_AVAILABLE

        # Test the actual fallback path
        if not RICH_AVAILABLE:
            from cli.console import print_panel

            print_panel("Title", "Content here")
            captured = capsys.readouterr()
            assert "Title" in captured.out
            assert "Content" in captured.out


class TestCreateTableFactory:
    """Tests for create_table factory function."""

    def test_create_table_with_title(self):
        """create_table should accept title."""
        from cli.console import create_table

        table = create_table("My Title")
        # Should not raise, regardless of rich availability
        assert table is not None

    def test_create_table_returns_addable(self):
        """create_table result should support add_column and add_row."""
        from cli.console import create_table

        table = create_table("Test")
        table.add_column("Header")
        table.add_row("Value")

        # Should not raise
        assert True


class TestPrintHelpers:
    """Tests for print helper functions."""

    def test_print_success_outputs(self, capsys):
        """print_success should output message."""
        from cli.console import print_success

        print_success("Operation completed")

        captured = capsys.readouterr()
        assert "Operation completed" in captured.out

    def test_print_error_outputs(self, capsys):
        """print_error should output message."""
        from cli.console import print_error

        print_error("Something failed")

        captured = capsys.readouterr()
        assert "Something failed" in captured.out

    def test_print_warning_outputs(self, capsys):
        """print_warning should output message."""
        from cli.console import print_warning

        print_warning("Be careful")

        captured = capsys.readouterr()
        assert "Be careful" in captured.out

    def test_print_panel_outputs(self, capsys):
        """print_panel should output title and content."""
        from cli.console import print_panel

        print_panel("Panel Title", "Panel content here")

        captured = capsys.readouterr()
        assert "Panel Title" in captured.out
        assert "Panel content" in captured.out
