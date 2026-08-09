"""webspider.mcp_client — MCP connector to ether-websearch.

Loads the 15 tools from ether-websearch's MCP server via smolagents' MCPClient
stdio subprocess transport.

Requires the ether-websearch REST core to be running (MCP_REST_BASE_URL).
Use `just up` to start both services.

Usage:
    from webspider.mcp_client import get_mcp_tools

    with get_mcp_tools() as tools:
        agent = CodeAgent(tools=tools, model=model)
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any


def get_mcp_tools() -> Any:
    """Load MCP tools from ether-websearch via stdio subprocess.

    Returns:
        A context manager that yields the list of tools when entered.
        Use within a `with` block::

            with get_mcp_tools() as tools:
                agent = CodeAgent(tools=tools, ...)

    Raises:
        RuntimeError: If ether-websearch-mcp entry point is not found.
        ImportError: If smolagents MCPClient is not available.
    """
    try:
        from mcp import StdioServerParameters
        from smolagents import MCPClient
    except ImportError as e:
        raise ImportError(
            "smolagents MCPClient requires smolagents>=1.10 and mcp>=1.2. Install with: uv pip install -e '.'"
        ) from e

    command = _find_mcp_command()
    env = {**os.environ}
    env.setdefault("MCP_REST_BASE_URL", "http://127.0.0.1:8766")

    server_parameters = StdioServerParameters(
        command=command[0],
        args=command[1:],
        env=env,
    )

    return MCPClient(server_parameters, structured_output=True)


def _find_mcp_command() -> list[str]:
    """Find the ether-websearch-mcp entry point.

    Prefers the entry point from the installed package, falls back to
    using the sibling ether-websearch repo's venv Python.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "websearch.src.mcp.mcp_server", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return [sys.executable, "-m", "websearch.src.mcp.mcp_server"]
    except Exception:
        pass

    websearch_repo = os.environ.get(
        "ETHER_WEBSEARCH_REPO",
        os.path.join(os.path.dirname(__file__), "..", "..", "ether-websearch"),
    )
    websearch_repo = os.path.abspath(websearch_repo)
    venv_python = os.path.join(websearch_repo, ".venv", "bin", "python")

    if os.path.isfile(venv_python):
        return [venv_python, "-m", "websearch.src.mcp.mcp_server"]

    raise RuntimeError(
        "Cannot find ether-websearch-mcp entry point. "
        "Ensure ether-websearch is installed or set ETHER_WEBSEARCH_REPO "
        "to the correct path."
    )
