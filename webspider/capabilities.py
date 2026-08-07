"""webspider.capabilities — Capability inventory and gap detection.

Provides:
    - Capability inventory (from MCP resources).
    - request_capability tool: writes feature requests to ether-websearch backlog.

Usage:
    from webspider.capabilities import get_capabilities_tools

    tools = get_capabilities_tools()
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime


def get_capabilities_tools() -> list[Callable]:
    """Return capability-related tools for the agent.

    Returns:
        List of callable tool functions.
    """
    return [
        request_capability,
    ]


def _get_ether_websearch_intake_path() -> str:
    """Resolve the ether-websearch intake IDEAS.md path."""
    repo = os.environ.get(
        "ETHER_WEBSEARCH_REPO",
        os.path.join(os.path.dirname(__file__), "..", "..", "ether-websearch"),
    )
    repo = os.path.abspath(repo)
    return os.path.join(repo, "spec-native", "intake", "IDEAS.md")


def request_capability(name: str, description: str, use_case: str) -> str:
    """Request a new capability from ether-websearch.

    Writes a structured feature request to the ether-websearch SpecNative
    intake backlog.

    Args:
        name: Short name for the capability (e.g. "sitemap_xml_fetch").
        description: What the capability should do.
        use_case: Why it's needed — the concrete scenario encountered.

    Returns:
        Confirmation message with the path where the request was written.
    """
    intake_path = _get_ether_websearch_intake_path()
    os.makedirs(os.path.dirname(intake_path), exist_ok=True)

    request_entry = {
        "capability": name,
        "description": description,
        "use_case": use_case,
        "requested_by": "ether-webspider",
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    markdown_entry = _format_request_markdown(request_entry)

    with open(intake_path, "a", encoding="utf-8") as f:
        f.write(markdown_entry)

    return f"Capability request '{name}' written to {intake_path}"


def _format_request_markdown(entry: dict) -> str:
    """Format a capability request as a Markdown entry for IDEAS.md."""
    return f"""
## Capability Request — {entry["capability"]}

- **Timestamp:** {entry["timestamp"]}
- **Requested by:** {entry["requested_by"]}

### Description

{entry["description"]}

### Use Case

{entry["use_case"]}

---
"""
