"""Tests for webspider.capabilities — request_capability tool."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest


@pytest.fixture
def ether_websearch_temp() -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_request_capability_writes_to_backlog(ether_websearch_temp: str) -> None:
    """request_capability appends a feature request to IDEAS.md."""
    with patch.dict(os.environ, {"ETHER_WEBSEARCH_REPO": ether_websearch_temp}):
        from webspider.capabilities import request_capability

        result = request_capability(
            name="sitemap_xml_fetch",
            description="Fetch and parse sitemap.xml to discover URLs.",
            use_case="During crawl of https://example.com, need sitemap discovery.",
        )

        assert "sitemap_xml_fetch" in result

        ideas_path = os.path.join(ether_websearch_temp, "spec-native", "intake", "IDEAS.md")
        assert os.path.isfile(ideas_path)

        with open(ideas_path) as f:
            content = f.read()

        assert "sitemap_xml_fetch" in content
        assert "Fetch and parse sitemap.xml" in content
        assert "ether-webspider" in content
        assert "During crawl" in content


def test_request_capability_appends_not_overwrites(ether_websearch_temp: str) -> None:
    """Multiple request_capability calls append to IDEAS.md."""
    with patch.dict(os.environ, {"ETHER_WEBSEARCH_REPO": ether_websearch_temp}):
        from webspider.capabilities import request_capability

        request_capability("cap_a", "desc a", "use case a")
        request_capability("cap_b", "desc b", "use case b")

        ideas_path = os.path.join(ether_websearch_temp, "spec-native", "intake", "IDEAS.md")
        with open(ideas_path) as f:
            content = f.read()

        assert "cap_a" in content
        assert "cap_b" in content


def test_request_capability_custom_repo_path(ether_websearch_temp: str) -> None:
    """ETHER_WEBSEARCH_REPO env var controls the target repo."""
    custom = os.path.join(ether_websearch_temp, "custom-repo")
    os.makedirs(os.path.join(custom, "spec-native", "intake"))

    with patch.dict(os.environ, {"ETHER_WEBSEARCH_REPO": custom}):
        from webspider.capabilities import request_capability

        request_capability("test_cap", "test desc", "test use case")

        ideas_path = os.path.join(custom, "spec-native", "intake", "IDEAS.md")
        assert os.path.isfile(ideas_path)


def test_get_capabilities_tools_returns_list() -> None:
    """get_capabilities_tools returns a list of callables."""
    from webspider.capabilities import get_capabilities_tools

    tools = get_capabilities_tools()
    assert isinstance(tools, list)
    assert len(tools) >= 1
    assert callable(tools[0])
