"""Tests for the wikimcp CLI using Click's CliRunner."""
import pytest
from pathlib import Path
from click.testing import CliRunner

from wikimcp.cli import main


def test_help_exits_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "wikimcp" in result.output.lower()


def test_version_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_init_command_creates_wiki(tmp_path: Path) -> None:
    runner = CliRunner()
    wiki_dir = tmp_path / "my-wiki"
    result = runner.invoke(main, ["init", "--wiki-dir", str(wiki_dir)])
    assert result.exit_code == 0, result.output
    # Wiki directory and key files should have been created
    assert wiki_dir.is_dir()
    assert (wiki_dir / "CLAUDE.md").exists()
    assert (wiki_dir / "wiki" / "index.md").exists()
    assert (wiki_dir / ".git").is_dir()


def test_init_command_output_contains_snippet(tmp_path: Path) -> None:
    runner = CliRunner()
    wiki_dir = tmp_path / "my-wiki"
    result = runner.invoke(main, ["init", "--wiki-dir", str(wiki_dir)])
    assert result.exit_code == 0, result.output
    # The MCP config snippet should be printed
    assert "mcpServers" in result.output or "wikimcp" in result.output


def test_serve_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["serve", "--help"])
    assert result.exit_code == 0
    assert "wiki-dir" in result.output


def test_server_subcommand_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["server", "--help"])
    assert result.exit_code == 0


def test_add_user_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["add-user", "--help"])
    assert result.exit_code == 0


def test_list_users_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["list-users", "--help"])
    assert result.exit_code == 0
