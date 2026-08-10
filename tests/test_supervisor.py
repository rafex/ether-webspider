"""MissionSupervisor control and one-step execution tests."""

from __future__ import annotations

import os
import tempfile
import time
from unittest.mock import patch


def _fake_model():
    from smolagents import ChatMessage, MessageRole, Model

    class FakeModel(Model):
        def generate(self, messages, stop_sequences=None, grammar=None, **kwargs):
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content="<code>final_answer('supervisor complete')</code>",
            )

    return FakeModel()


def test_supervisor_can_run_and_publish_events():
    with (
        tempfile.TemporaryDirectory() as checkpoint_dir,
        patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}),
    ):
        from webspider.mission import mission_from_args
        from webspider.supervisor import MissionSupervisor

        mission = mission_from_args("Find API", "https://example.com", max_steps=3)
        supervisor = MissionSupervisor(mission, model=_fake_model(), mission_id="sup-test")
        supervisor.start()
        deadline = time.time() + 5
        while not supervisor.status()["done"] and time.time() < deadline:
            time.sleep(0.02)

        assert supervisor.status()["done"] is True
        assert supervisor.result()["ok"] is True
        assert any(event["type"] == "mission.completed" for event in supervisor.events())


def test_supervisor_takeover_and_instruction_are_shared_state():
    from webspider.mission import mission_from_args
    from webspider.supervisor import MissionSupervisor

    mission = mission_from_args("Find API", "https://example.com", interaction_mode="hybrid")
    supervisor = MissionSupervisor(mission, model=_fake_model(), mission_id="control-test")
    assert supervisor.control("takeover")["control"] == "takeover"
    supervisor.send_message("No envíes formularios todavía")
    assert supervisor.status()["control"] == "takeover"
    assert supervisor.control("release")["control"] == "running"


def test_interactive_supervisor_waits_for_user_instruction():
    with (
        tempfile.TemporaryDirectory() as checkpoint_dir,
        patch.dict(os.environ, {"WEBSPIDER_CHECKPOINTS": checkpoint_dir}),
    ):
        from webspider.mission import mission_from_args
        from webspider.supervisor import MissionSupervisor

        mission = mission_from_args("Find API", "https://example.com", interaction_mode="interactive")
        supervisor = MissionSupervisor(mission, model=_fake_model(), mission_id="interactive-test")
        supervisor.start()
        time.sleep(0.1)
        assert supervisor.status()["done"] is False
        supervisor.send_message("Empieza con la página inicial")
        deadline = time.time() + 5
        while not supervisor.status()["done"] and time.time() < deadline:
            time.sleep(0.02)
        assert supervisor.status()["done"] is True
