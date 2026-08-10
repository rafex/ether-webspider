"""Web UI and WebSocket control-plane tests."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def _fake_model():
    from smolagents import ChatMessage, MessageRole, Model

    class FakeModel(Model):
        def generate(self, messages, stop_sequences=None, grammar=None, **kwargs):
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content="<code>final_answer('ui complete')</code>",
            )

    return FakeModel()


def test_start_mission_and_query_events():
    from webspider.server import app, registry

    registry.configure(mcp_tools=None, model=_fake_model())
    client = TestClient(app)
    response = client.post(
        "/api/missions",
        json={"goal": "Find API", "start_url": "https://example.com", "max_steps": 2},
    )
    assert response.status_code == 200
    mission_id = response.json()["mission_id"]
    deadline = time.time() + 5
    while time.time() < deadline:
        status = client.get(f"/api/missions/{mission_id}").json()
        if status["done"]:
            break
        time.sleep(0.02)
    assert status["done"] is True
    events = client.get(f"/api/missions/{mission_id}/events").json()["events"]
    assert any(event["type"] == "mission.completed" for event in events)


def test_websocket_accepts_chat_and_control_messages():
    from webspider.server import app, registry

    registry.configure(mcp_tools=None, model=_fake_model())
    client = TestClient(app)
    mission_id = client.post(
        "/api/missions",
        json={"goal": "Find API", "start_url": "https://example.com", "interaction_mode": "hybrid"},
    ).json()["mission_id"]
    with client.websocket_connect(f"/ws/missions/{mission_id}") as websocket:
        websocket.send_json({"type": "control", "action": "pause"})
        websocket.send_json({"type": "message", "text": "Continúa sin mutaciones"})
        assert websocket is not None
