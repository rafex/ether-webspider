"""Tests for webspider.agent — CodeAgent integration with FakeModel.

Validates that run_mission and resume_mission complete without crash
and write proper checkpoints. Uses a FakeModel that returns a
deterministic final_answer response.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest


def _get_fake_model():
    """Create a FakeModel that stops the agent immediately with a final answer."""
    from smolagents import ChatMessage, MessageRole, Model

    class FakeModel(Model):
        def generate(self, messages, stop_sequences=None, grammar=None, **kwargs):
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content="<code>final_answer('Mission completed. Test successful.')</code>",
            )

    return FakeModel()


@pytest.fixture
def checkpoint_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_run_mission_completes_and_writes_checkpoint(checkpoint_dir: str) -> None:
    """run_mission with a FakeModel completes, returns ok, writes checkpoint files."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.agent import run_mission
        from webspider.mission import mission_from_args

        mission = mission_from_args(
            goal="Find the login page",
            start="https://example.com",
            max_steps=5,
        )
        model = _get_fake_model()

        result = run_mission(mission, mcp_tools=None, model=model, mission_id="fake_m1")

        assert result["ok"] is True
        assert result["mission_id"] == "fake_m1"
        assert "test successful" in result["result"].lower()

        # Checkpoint files exist
        state_path = os.path.join(checkpoint_dir, "fake_m1", "state.json")
        memory_path = os.path.join(checkpoint_dir, "fake_m1", "memory.jsonl")
        assert os.path.isfile(state_path)
        assert os.path.isfile(memory_path)

        # state.json contains the mission
        import json

        with open(state_path) as f:
            state = json.load(f)
        assert state["mission"]["goal"] == "Find the login page"

        # memory.jsonl is not empty
        with open(memory_path) as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) >= 1


def test_run_mission_with_error_returns_ok_false(checkpoint_dir: str) -> None:
    """run_mission gracefully catches errors and returns ok=False with checkpoint."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.agent import run_mission
        from webspider.mission import mission_from_args

        mission = mission_from_args(goal="Test", start="https://x.com", max_steps=1)

        from smolagents import Model

        class BrokenModel(Model):
            def generate(self, messages, stop_sequences=None, grammar=None, **kwargs):
                raise RuntimeError("simulated LLM failure")

        model = BrokenModel()

        result = run_mission(mission, mcp_tools=None, model=model, mission_id="broken_m1")

        assert result["ok"] is False
        # Error is something from the model — verify it's non-empty
        assert len(result["error"]) > 0

        # Checkpoint still written
        state_path = os.path.join(checkpoint_dir, "broken_m1", "state.json")
        assert os.path.isfile(state_path)


def test_resume_mission_no_checkpoint_raises() -> None:
    """resume_mission raises ValueError when checkpoint does not exist."""
    from webspider.agent import resume_mission

    with pytest.raises(ValueError, match="No checkpoint found"):
        resume_mission("nonexistent_mission_id")


def test_resume_mission_restores_state(checkpoint_dir: str) -> None:
    """resume_mission from a pre-seeded checkpoint continues and updates the checkpoint."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        import json

        from webspider.agent import resume_mission
        from webspider.checkpoint import save_checkpoint, save_memory

        # Seed a checkpoint with state and memory
        seed_state = {
            "mission": {"goal": "Find pricing page", "start_url": "https://shop.com", "max_steps": 10},
            "step": 3,
            "visited": ["https://shop.com", "https://shop.com/products"],
            "frontier": [{"url": "https://shop.com/pricing", "priority": 0.9, "reason": "pricing link"}],
            "findings": [{"url": "https://shop.com/api/v1", "type": "rest_api", "confidence": 0.7, "notes": ""}],
        }
        save_checkpoint("resume_test", seed_state)

        # Seed memory with a plausible step
        save_memory(
            "resume_test",
            [
                {"step_number": 1, "observations": "exploring homepage", "model_output": ""},
                {"step_number": 2, "observations": "found products page", "model_output": ""},
                {"step_number": 3, "observations": "continuing", "model_output": ""},
            ],
        )

        model = _get_fake_model()

        result = resume_mission("resume_test", mcp_tools=None, model=model)

        # Should complete without crash
        assert result["ok"] is True
        assert result["mission_id"] == "resume_test"

        # Re-checkpoint should exist with updated state
        state_path = os.path.join(checkpoint_dir, "resume_test", "state.json")
        with open(state_path) as f:
            updated_state = json.load(f)
        assert updated_state["mission"]["goal"] == "Find pricing page"


def test_run_mission_auto_generates_id(checkpoint_dir: str) -> None:
    """run_mission generates a mission_id when none is provided."""
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}):
        from webspider.agent import run_mission
        from webspider.mission import mission_from_args

        mission = mission_from_args(goal="Autogenerated", start="https://x.com", max_steps=3)
        model = _get_fake_model()

        result = run_mission(mission, mcp_tools=None, model=model)

    assert result["mission_id"].startswith("m")
    assert len(result["mission_id"]) > 10


def test_state_tools_are_registered() -> None:
    """The agent tool dict includes add_finding, mark_visited, add_to_frontier, etc."""
    from webspider.agent import _build_state_ref, _get_agent_tools

    state_ref = _build_state_ref({"goal": "T", "start_url": "S", "max_steps": 5})
    tools = _get_agent_tools([], "test_m", state_ref)

    required = {"add_finding", "mark_visited", "add_to_frontier", "state_summary", "save_checkpoint", "load_checkpoint"}
    assert required.issubset(set(tools.keys()))
