"""Tests for webspider.mission — mission parsing and prompt building."""

from __future__ import annotations

import json
import os
import tempfile

import pytest


def test_mission_from_args_basic() -> None:
    """Basic mission creation from CLI args."""
    from webspider.mission import mission_from_args

    mission = mission_from_args(
        goal="Find login endpoint",
        start="https://example.com",
        max_steps=15,
    )

    assert mission["goal"] == "Find login endpoint"
    assert mission["start_url"] == "https://example.com"
    assert mission["max_steps"] == 15
    assert mission["allowed_domains"] == []
    assert mission["disable_search"] is False


def test_mission_from_args_with_domains() -> None:
    """Mission with allowed_domains restriction."""
    from webspider.mission import mission_from_args

    mission = mission_from_args(
        goal="Find API",
        start="https://api.example.com",
        allowed_domains=["example.com", "api.example.com"],
        disable_search=True,
    )

    assert len(mission["allowed_domains"]) == 2
    assert mission["disable_search"] is True


def test_mission_from_file() -> None:
    """Load mission from valid JSON file."""
    from webspider.mission import mission_from_file

    data = {
        "goal": "Find the admin panel",
        "start_url": "https://site.com",
        "max_steps": 20,
        "allowed_domains": ["site.com"],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        mission = mission_from_file(path)
        assert mission["goal"] == "Find the admin panel"
        assert mission["start_url"] == "https://site.com"
        assert mission["max_steps"] == 20
        assert mission["allowed_domains"] == ["site.com"]
    finally:
        os.unlink(path)


def test_mission_from_file_missing_keys() -> None:
    """Mission file without required keys raises ValueError."""
    from webspider.mission import mission_from_file

    data = {"goal": "test"}  # missing start_url

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        with pytest.raises(ValueError, match="start_url"):
            mission_from_file(path)
    finally:
        os.unlink(path)


def test_mission_from_file_defaults() -> None:
    """Mission file with only required keys gets correct defaults."""
    from webspider.mission import mission_from_file

    data = {"goal": "T", "start_url": "S"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        mission = mission_from_file(path)
        assert mission["max_steps"] == 30
        assert mission["allowed_domains"] == []
        assert mission["disable_search"] is False
    finally:
        os.unlink(path)


def test_build_prompt_contains_goal() -> None:
    """Prompt includes the mission goal."""
    from webspider.mission import build_prompt, mission_from_args

    mission = mission_from_args(
        goal="Find the login portal for the SAT",
        start="https://www.sat.gob.mx",
    )
    prompt = build_prompt(mission)

    assert "Find the login portal for the SAT" in prompt
    assert "https://www.sat.gob.mx" in prompt
    assert "spider_webpage" in prompt
    assert "save_checkpoint" in prompt
    assert "request_capability" in prompt


def test_build_prompt_with_domains() -> None:
    """Prompt includes domain restriction when specified."""
    from webspider.mission import build_prompt, mission_from_args

    mission = mission_from_args(
        goal="Test",
        start="https://x.com",
        allowed_domains=["x.com"],
    )
    prompt = build_prompt(mission)

    assert "x.com" in prompt
    assert "within these domains" in prompt


def test_build_prompt_no_search() -> None:
    """Prompt does not include search_duckduckgo usage hint when search is disabled."""
    from webspider.mission import build_prompt, mission_from_args

    mission = mission_from_args(
        goal="Test",
        start="https://x.com",
        disable_search=True,
    )
    prompt = build_prompt(mission)

    # The search hint (not the tool list) should be absent
    assert "can use `search_duckduckgo`" not in prompt


def test_build_resume_prompt() -> None:
    """Resume prompt includes checkpoint state summary."""
    from webspider.mission import build_resume_prompt

    mission = {
        "goal": "Find login",
        "start_url": "https://example.com",
        "max_steps": 30,
    }
    state = {
        "step": 10,
        "visited": ["https://example.com", "https://example.com/about"],
        "frontier": [
            {"url": "https://example.com/login", "priority": 0.95},
            {"url": "https://example.com/api", "priority": 0.7},
        ],
        "findings": [
            {"url": "https://example.com/login.aspx", "type": "login"},
        ],
    }

    prompt = build_resume_prompt(mission, state)

    assert "step 10" in prompt
    assert "2 URLs visited" in prompt
    assert "1 findings" in prompt
    assert "2 URLs in frontier" in prompt
    assert "login.aspx" in prompt
    assert "priority: 0.95" in prompt
