"""Tests for webspider.checkpoint — state persistence and resume."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest


@pytest.fixture
def checkpoint_dir() -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


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


def test_save_and_load_memory(checkpoint_dir: str) -> None:
    """Round-trip: save and load agent memory steps."""
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


def test_load_memory_nonexistent(checkpoint_dir: str) -> None:
    """Loading memory for nonexistent mission returns empty list."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import load_memory

        loaded = load_memory("nonexistent")
        assert loaded == []


def test_save_checkpoint_tool(checkpoint_dir: str) -> None:
    """create_save_checkpoint_tool produces a callable that persists state."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import create_save_checkpoint_tool, load_checkpoint

        state_ref = {
            "mission": {"goal": "test", "start_url": "http://x", "max_steps": 5},
            "step": 3,
            "visited": [],
            "frontier": [],
            "findings": [],
        }

        tool = create_save_checkpoint_tool("tool_test", state_ref)
        result = tool("testing save")

        assert "Checkpoint saved" in result
        loaded = load_checkpoint("tool_test")
        assert loaded is not None
        assert loaded["step"] == 3
        assert loaded["checkpoint_reason"] == "testing save"


def test_load_checkpoint_tool(checkpoint_dir: str) -> None:
    """create_load_checkpoint_tool restores state into the mutable reference."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.checkpoint import create_load_checkpoint_tool, save_checkpoint

        save_checkpoint(
            "load_tool_test",
            {
                "mission": {"goal": "test", "start_url": "http://x", "max_steps": 5},
                "step": 7,
                "visited": ["http://x", "http://x/y"],
                "frontier": [{"url": "http://x/z", "priority": 0.5}],
                "findings": [{"url": "http://x/l", "type": "form"}],
            },
        )

        state_ref: dict = {}
        tool = create_load_checkpoint_tool("load_tool_test", state_ref)
        result = tool()

        assert "Checkpoint loaded" in result
        assert state_ref["step"] == 7
        assert len(state_ref["visited"]) == 2
        assert len(state_ref["frontier"]) == 1
        assert len(state_ref["findings"]) == 1
