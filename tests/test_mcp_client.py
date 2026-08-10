"""Tests for resolving the ether-websearch MCP command."""

from __future__ import annotations

import os

import pytest


def test_find_mcp_command_prefers_configured_local_repo(tmp_path, monkeypatch) -> None:
    """The configured ether-websearch checkout is authoritative."""
    python_bin = tmp_path / ".venv" / "bin" / "python"
    python_bin.parent.mkdir(parents=True)
    python_bin.touch()
    monkeypatch.setenv("ETHER_WEBSEARCH_REPO", str(tmp_path))

    from webspider.mcp_client import _find_mcp_command

    assert _find_mcp_command() == [
        os.fspath(python_bin),
        "-m",
        "websearch.src.mcp.mcp_server",
    ]


def test_find_mcp_command_rejects_missing_configured_repo(tmp_path, monkeypatch) -> None:
    """A bad explicit path must not silently select another installation."""
    monkeypatch.setenv("ETHER_WEBSEARCH_REPO", str(tmp_path / "missing"))

    from webspider.mcp_client import _find_mcp_command

    with pytest.raises(RuntimeError, match="Cannot find ether-websearch Python environment"):
        _find_mcp_command()
