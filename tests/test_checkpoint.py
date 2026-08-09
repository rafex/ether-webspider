"""Tests for webspider.checkpoint — state persistence, memory serialization, and state tools."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

import pytest


@pytest.fixture
def checkpoint_dir() -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ── save / load checkpoint ─────────────────────────────────────────────────


def test_save_and_load_checkpoint(checkpoint_dir: str) -> None:
    """Round-trip: save checkpoint and load it back."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import load_checkpoint, save_checkpoint

        state = {
            "mission": {"goal": "Find login", "start_url": "https://example.com", "max_steps": 10},
            "step": 5,
            "visited": ["https://example.com", "https://example.com/about"],
            "frontier": [{"url": "https://example.com/login", "priority": 0.9}],
            "findings": [{"url": "https://example.com/login.aspx", "type": "login"}],
        }

        path = save_checkpoint("test_mission", state)
        assert os.path.isfile(path)

        loaded = load_checkpoint("test_mission")
        assert loaded is not None
        assert loaded["step"] == 5
        assert loaded["mission_id"] == "test_mission"
        assert len(loaded["visited"]) == 2
        assert len(loaded["frontier"]) == 1
        assert len(loaded["findings"]) == 1
        assert "last_step_at" in loaded


def test_load_nonexistent_checkpoint(checkpoint_dir: str) -> None:
    """Loading a nonexistent checkpoint returns None."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import load_checkpoint

        result = load_checkpoint("nonexistent")
        assert result is None


# ── save / load memory ─────────────────────────────────────────────────────


def test_save_and_load_memory_dicts(checkpoint_dir: str) -> None:
    """Round-trip: save and load memory steps as plain dicts."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import load_memory, save_memory

        steps = [
            {"type": "task", "task": "Find login"},
            {"type": "action", "step": 1, "llm_output": "starting exploration"},
        ]

        path = save_memory("test_mission", steps)
        assert os.path.isfile(path)

        loaded = load_memory("test_mission")
        assert len(loaded) == 2
        assert loaded[0]["type"] == "task"
        assert loaded[1]["step"] == 1


def test_save_memory_with_smolagents_objects(checkpoint_dir: str) -> None:
    """save_memory handles smolagents ActionStep objects (uses .dict())."""
    try:
        from smolagents.memory import ActionStep, Timing
    except ImportError:
        pytest.skip("smolagents not installed")

    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        import time

        from webspider.checkpoint import load_memory, save_memory

        step = ActionStep(
            step_number=1,
            timing=Timing(start_time=time.time()),
            observations="fetching page",
        )

        path = save_memory("action_test", [step])
        assert os.path.isfile(path)

        loaded = load_memory("action_test")
        assert len(loaded) >= 1
        # Should contain real data, not error placeholder
        assert loaded[0].get("step_number") == 1
        assert loaded[0].get("observations") == "fetching page"


def test_load_memory_nonexistent(checkpoint_dir: str) -> None:
    """Loading memory for nonexistent mission returns empty list."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import load_memory

        loaded = load_memory("nonexistent")
        assert loaded == []


def test_save_memory_unserializable_object(checkpoint_dir: str) -> None:
    """save_memory gracefully handles unserializable objects (error placeholder)."""

    class WeirdObject:
        pass

    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import load_memory, save_memory

        save_memory("weird_test", [WeirdObject()])

        loaded = load_memory("weird_test")
        assert len(loaded) >= 1
        # Fallback used repr, not error placeholder
        assert "step_type" in loaded[0] or "repr" in loaded[0]


# ── state tools ─────────────────────────────────────────────────────────────


def test_state_tools_save_and_load(checkpoint_dir: str) -> None:
    """create_state_tools save_checkpoint / load_checkpoint round-trip."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import create_state_tools, load_checkpoint

        state_ref = {
            "mission": {"goal": "test", "start_url": "http://x", "max_steps": 5},
            "step": 3,
            "visited": ["http://x"],
            "frontier": [],
            "findings": [],
        }
        tools = create_state_tools("tool_test", state_ref)

        result = tools["save_checkpoint"]("testing save")
        assert "Checkpoint saved" in result

        loaded = load_checkpoint("tool_test")
        assert loaded is not None
        assert loaded["step"] == 3
        assert loaded["checkpoint_reason"] == "testing save"

        # load CP into a fresh ref
        fresh_ref: dict = {}
        tools2 = create_state_tools("tool_test", fresh_ref)
        result2 = tools2["load_checkpoint"]()
        assert "Checkpoint loaded" in result2
        assert fresh_ref["step"] == 3
        assert fresh_ref["visited"] == ["http://x"]


def test_add_finding_tool(checkpoint_dir: str) -> None:
    """add_finding registers and deduplicates findings."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import create_state_tools

        state_ref: dict = {}
        tools = create_state_tools("f_test", state_ref)

        r1 = tools["add_finding"]("https://x.com/login.aspx", "login", 0.95, "main login")
        assert "Finding added" in r1
        assert len(state_ref["findings"]) == 1

        # Same URL — should update
        r2 = tools["add_finding"]("https://x.com/login.aspx", "login", 0.99, "updated")
        assert "Updated finding" in r2
        assert len(state_ref["findings"]) == 1
        assert state_ref["findings"][0]["confidence"] == 0.99


def test_mark_visited_tool(checkpoint_dir: str) -> None:
    """mark_visited adds and deduplicates URLs."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import create_state_tools

        state_ref: dict = {}
        tools = create_state_tools("v_test", state_ref)

        tools["mark_visited"]("https://x.com")
        tools["mark_visited"]("https://x.com")  # no dup
        assert state_ref["visited"] == ["https://x.com"]


def test_add_to_frontier_tool(checkpoint_dir: str) -> None:
    """add_to_frontier adds URLs with priority and deduplicates."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import create_state_tools

        state_ref: dict = {}
        tools = create_state_tools("fr_test", state_ref)

        tools["add_to_frontier"]("https://x.com/login", 0.9, "login link")
        tools["add_to_frontier"]("https://x.com/api", 0.7, "api link")
        tools["add_to_frontier"]("https://x.com/login", 0.5, "dup")  # keeps higher priority

        assert len(state_ref["frontier"]) == 2
        assert state_ref["frontier"][0]["priority"] == 0.9


def test_state_summary_tool(checkpoint_dir: str) -> None:
    """state_summary returns a JSON summary of current state."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import create_state_tools

        state_ref = {
            "mission": {"goal": "g", "start_url": "s", "max_steps": 5},
            "step": 2,
            "visited": ["a", "b"],
            "frontier": [{"url": "c", "priority": 0.9}],
            "findings": [{"url": "d", "type": "login"}],
        }
        tools = create_state_tools("sum_test", state_ref)

        summary = tools["state_summary"]()
        data = json.loads(summary)
        assert data["visited_count"] == 2
        assert data["frontier_count"] == 1
        assert data["findings_count"] == 1


# ── step callback ───────────────────────────────────────────────────────────


def test_step_callback_no_agent(checkpoint_dir: str) -> None:
    """create_step_callback returns a callable that silently returns when no agent."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import create_step_callback

        cb = create_step_callback("scb_test")
        # Called without agent (synthetic test)
        cb(memory_step=None, agent=None)

        # No crash, no file created (no steps to save)
        memory_path = os.path.join(checkpoint_dir, "scb_test", "memory.jsonl")
        # File not created since agent is None
        assert not os.path.isfile(memory_path)


def test_step_callback_with_mock_agent(checkpoint_dir: str) -> None:
    """Step callback saves memory when agent has memory.steps."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import create_step_callback, load_memory

        cb = create_step_callback("scb_agent_test")

        # Mock an agent-like object with memory.steps
        class Memory:
            steps = [{"step_number": 1, "observations": "test"}]

        class FakeAgent:
            memory = Memory()

        cb(memory_step=None, agent=FakeAgent())

        memory_path = os.path.join(checkpoint_dir, "scb_agent_test", "memory.jsonl")
        assert os.path.isfile(memory_path)

        loaded = load_memory("scb_agent_test")
        assert len(loaded) >= 1
        assert loaded[0].get("step_number") == 1
