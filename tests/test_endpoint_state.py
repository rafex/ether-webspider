"""Structured endpoint state and secret handling tests."""

from __future__ import annotations

import json
import os
from unittest.mock import patch


def test_record_request_deduplicates_by_method_url_and_body(tmp_path):
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": str(tmp_path)}):
        from webspider.checkpoint import create_state_tools

        state = {
            "mission": {"allowed_domains": ["example.com"], "max_requests": 2},
            "requests": [],
            "findings": [],
        }
        tools = create_state_tools("requests", state)
        first = {"url": "https://example.com/api?a=1&b=2", "method": "post", "body": {"id": 1}, "source": "js"}
        assert "Request recorded" in tools["record_request"](first)
        assert "already captured" in tools["record_request"]({**first, "url": "https://example.com/api?b=2&a=1"})
        assert "Request recorded" in tools["record_request"]({**first, "body": {"id": 2}})
        assert len(state["requests"]) == 2
        assert len(state["findings"]) == 2


def test_checkpoint_redacts_secrets_in_state_and_memory(tmp_path):
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": str(tmp_path)}):
        from webspider.checkpoint import load_checkpoint, save_checkpoint, save_memory

        save_checkpoint(
            "secrets",
            {
                "mission": {"goal": "test"},
                "requests": [{"headers": {"Authorization": "Bearer top-secret", "Cookie": "sid=abc"}}],
                "notes": "password=hunter2",
            },
        )
        save_memory("secrets", [{"model_output": "Authorization: Bearer top-secret; token=hunter2"}])

        state_text = (tmp_path / "secrets" / "state.json").read_text()
        memory_text = (tmp_path / "secrets" / "memory.jsonl").read_text()
        assert "top-secret" not in state_text
        assert "hunter2" not in state_text
        assert "top-secret" not in memory_text
        assert "hunter2" not in memory_text
        assert load_checkpoint("secrets")["requests"][0]["headers"]["Authorization"] == "[REDACTED]"
        assert json.loads(memory_text)["model_output"].startswith("Authorization")


def test_step_callback_increments_and_persists_state(tmp_path):
    with patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": str(tmp_path)}):
        from webspider.checkpoint import create_step_callback, load_checkpoint

        state = {"mission": {"goal": "test"}, "step": 0, "findings": []}
        callback = create_step_callback("steps", state)
        callback(agent=None)
        callback(agent=None)

        assert state["step"] == 2
        assert load_checkpoint("steps")["step"] == 2
