"""Interactive/autonomous mission supervisor shared by Web UI and REPL."""

from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from typing import Any, cast

from webspider.agent import (
    _build_state_ref,
    _generate_mission_id,
    _get_agent_tools,
    _require_mcp_capabilities,
    _validate_mission,
)
from webspider.checkpoint import create_step_callback, redact_sensitive_data, save_checkpoint
from webspider.config import get_model
from webspider.mission import build_prompt
from webspider.secrets import resolve_credentials


class MissionSupervisor:
    """Run one CodeAgent mission in controllable one-step turns."""

    def __init__(
        self,
        mission: dict[str, Any],
        mcp_tools: list | None = None,
        model: Any = None,
        mission_id: str | None = None,
        credentials: dict[str, str] | None = None,
    ) -> None:
        _validate_mission(mission)
        self.mission = mission
        self.mission_id = mission_id or _generate_mission_id(mission["goal"])
        self.mcp_tools = mcp_tools or []
        if mcp_tools is not None:
            _require_mcp_capabilities(mcp_tools)
        self.model = model or get_model()
        session_config = mission.get("session", {})
        self.credentials = resolve_credentials(credentials, session_config.get("credential_ref"))
        self.state = _build_state_ref(mission)
        # Runtime-only: checkpoint.py redacts this field before disk writes.
        # It is exposed solely through get_session_credentials() for an
        # explicitly authorized login recipe.
        self.state["runtime_credentials"] = dict(self.credentials)
        self.state["control"] = "running"
        self.state["user_instructions"] = []
        self.state["browser_session_id"] = mission.get("browser", {}).get("session_id")
        self._browser_event_cursor = 0
        self.tools: dict[str, Any] = {}
        self.agent: Any = None
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.run_event = threading.Event()
        if mission.get("interaction_mode") == "interactive":
            self.run_event.clear()
        else:
            self.run_event.set()
        self._lock = threading.RLock()
        self._events: deque[dict[str, Any]] = deque(maxlen=5_000)
        self._event_seq = 0
        self._done = threading.Event()
        self._result: dict[str, Any] | None = None

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self.thread and self.thread.is_alive():
                return self.status()
            self._prepare_agent()
            self.thread = threading.Thread(target=self._run, name=f"webspider-mission-{self.mission_id}", daemon=True)
            self.thread.start()
            self.emit("mission.started", {"mission_id": self.mission_id})
            return self.status()

    def _prepare_agent(self) -> None:
        from smolagents import CodeAgent

        self.tools = _get_agent_tools(self.mcp_tools, self.mission_id, self.state, on_finding=self._on_finding)
        self.tools["get_user_instruction"] = self.tools.get("get_user_instruction")
        self.agent = CodeAgent(
            tools=list(self.tools.values()),
            model=self.model,
            max_steps=self.mission["max_steps"],
            verbosity_level=2,
            step_callbacks=[create_step_callback(self.mission_id, self.state)],
        )

    def _run(self) -> None:
        try:
            self._start_browser_session_if_requested()
            prompt = build_prompt(self.mission)
            first_turn = True
            while not self.stop_event.is_set() and self.state.get("step", 0) < self.mission["max_steps"]:
                self.run_event.wait()
                if self.stop_event.is_set():
                    break
                reset_turn = first_turn
                task = (
                    prompt
                    if first_turn
                    else (
                        "Continue the mission from the current state. Call get_user_instruction() first, then "
                        "perform the next bounded discovery action and persist state."
                    )
                )
                first_turn = False
                self.emit("agent.thinking", {"step": self.state.get("step", 0) + 1})
                result = self.agent.run(task, reset=reset_turn, max_steps=1, return_full_result=True)
                output = str(getattr(result, "output", result) or "")
                self.emit("agent.step", {"step": self.state.get("step", 0), "output": output})
                if self._last_action_is_final():
                    break
            if self.stop_event.is_set():
                self.state["control"] = "stopped"
            else:
                self.state["control"] = "completed"
            save_checkpoint(self.mission_id, self.state)
            self._result = self._build_result(ok=True, result="Mission completed")
            self.emit("mission.completed", self._result)
        except Exception as exc:
            self.state["control"] = "error"
            self.state["error"] = str(exc)
            save_checkpoint(self.mission_id, self.state)
            self._result = self._build_result(ok=False, error=str(exc))
            self.emit("mission.error", {"error": str(exc)})
        finally:
            self._done.set()

    def _last_action_is_final(self) -> bool:
        steps = getattr(getattr(self.agent, "memory", None), "steps", [])
        for step in reversed(steps):
            if hasattr(step, "is_final_answer"):
                return bool(step.is_final_answer)
        return False

    def _start_browser_session_if_requested(self) -> None:
        browser = self.mission.get("browser", {})
        if (
            browser.get("attach")
            and not browser.get("session_id")
            and not self.mission.get("session", {}).get("attach_endpoint")
        ):
            raise ValueError("attach requires browser.session_id or session.attach_endpoint")
        if not browser.get("headed") and not browser.get("session_id"):
            return
        tool = self.tools.get("browser_session_start")
        if tool is None:
            self.emit("browser.unavailable", {"error": "browser_session_start is not available"})
            return
        response = tool(
            engine=browser.get("engine", "playwright"),
            browser=browser.get("browser", "chromium"),
            headed=bool(browser.get("headed", True)),
            allowed_domains=",".join(self.mission.get("allowed_domains", [])),
            session_id=browser.get("session_id"),
            storage_state_path=self.mission.get("session", {}).get("storage_state_path"),
            extra_headers=json.dumps(self.mission.get("session", {}).get("headers", {})),
            attach_endpoint=self.mission.get("session", {}).get("attach_endpoint"),
            max_requests=self.mission.get("max_requests", 200),
        )
        try:
            data = json.loads(response) if isinstance(response, str) else response
            session_id = data.get("session_id") or data.get("payload", {}).get("session_id")
            if session_id:
                self.state["browser_session_id"] = session_id
                self.mission.setdefault("browser", {})["session_id"] = session_id
                self.emit("browser.started", {"session_id": session_id})
        except (TypeError, json.JSONDecodeError):
            self.emit("browser.started", {"response": str(response)[:2_000]})
        login_actions = self.mission.get("session", {}).get("login_actions", [])
        for action in login_actions:
            self.browser_command(self._substitute_secrets(dict(action)), actor="system")
        self._drain_browser_events()

    def _substitute_secrets(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._substitute_secrets(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._substitute_secrets(item) for item in value]
        if isinstance(value, str):
            for key, secret in self.credentials.items():
                value = value.replace("{{" + key + "}}", secret)
        return value

    def _on_finding(self, finding: dict[str, Any]) -> None:
        self.emit("finding", finding)

    def send_message(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            raise ValueError("Message cannot be empty")
        with self._lock:
            self.state.setdefault("user_instructions", []).append({"text": text, "timestamp": time.time()})
            self.emit("user.message", {"text": text})
            if self.mission.get("interaction_mode") == "interactive":
                self.state["control"] = "running"
                self.run_event.set()
            save_checkpoint(self.mission_id, self.state)
            return self.status()

    def control(self, action: str) -> dict[str, Any]:
        action = action.lower().strip()
        with self._lock:
            if action in {"pause", "takeover"}:
                self.run_event.clear()
                self.state["control"] = "takeover" if action == "takeover" else "paused"
            elif action in {"resume", "release"}:
                self.state["control"] = "running"
                self.run_event.set()
            elif action == "stop":
                self.stop_event.set()
                self.run_event.set()
                self.state["control"] = "stopping"
                if self.agent is not None and hasattr(self.agent, "interrupt_switch"):
                    self.agent.interrupt_switch = True
            else:
                raise ValueError("control action must be pause, resume, takeover, release, or stop")
            self.emit(f"mission.{action}", {"control": self.state["control"]})
            self._browser_control(action)
            save_checkpoint(self.mission_id, self.state)
            return self.status()

    def _browser_control(self, action: str) -> None:
        session_id = self.state.get("browser_session_id")
        tool = self.tools.get("browser_session_command")
        if not session_id or tool is None or action not in {"pause", "resume", "takeover", "release"}:
            return
        try:
            tool(session_id=session_id, action=json.dumps({"type": action}), actor="user")
        except Exception as exc:
            self.emit("browser.control_error", {"error": str(exc)})

    def browser_command(self, action: dict[str, Any], actor: str = "user") -> dict[str, Any]:
        session_id = self.state.get("browser_session_id")
        tool = self.tools.get("browser_session_command")
        if not session_id or tool is None:
            raise RuntimeError("No persistent browser session is attached")
        response = tool(session_id=session_id, action=json.dumps(action), actor=actor)
        self.emit("browser.command", {"action": action})
        return {"response": response, "session_id": session_id}

    def events(self, after: int = 0) -> list[dict[str, Any]]:
        self._drain_browser_events()
        with self._lock:
            return [event for event in self._events if int(event["id"]) > after]

    def _drain_browser_events(self) -> None:
        """Mirror browser/network events into the mission event stream and state."""
        session_id = self.state.get("browser_session_id")
        tool = self.tools.get("browser_session_events")
        if not session_id or tool is None:
            return
        try:
            raw = tool(session_id=session_id, after=self._browser_event_cursor)
            payload = json.loads(raw) if isinstance(raw, str) else raw
            browser_events = payload.get("events", []) if isinstance(payload, dict) else []
            record_request = self.tools.get("record_request")
            for event in browser_events:
                event_id = int(event.get("id", 0))
                self._browser_event_cursor = max(self._browser_event_cursor, event_id)
                event_payload = event.get("payload", {})
                self.emit("browser.event", event)
                if event.get("type") == "network.request" and record_request is not None:
                    record_request(request=event_payload)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self.emit("browser.sync_error", {"error": str(exc)})

    def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._event_seq += 1
            self._events.append(
                {
                    "id": self._event_seq,
                    "timestamp": time.time(),
                    "mission_id": self.mission_id,
                    "type": event_type,
                    "payload": redact_sensitive_data(payload or {}),
                }
            )

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "mission_id": self.mission_id,
                "control": self.state.get("control", "running"),
                "step": self.state.get("step", 0),
                "requests_used": self.state.get("requests_used", 0),
                "visited_count": len(self.state.get("visited", [])),
                "findings_count": len(self.state.get("findings", [])),
                "findings": redact_sensitive_data(self.state.get("findings", [])[-200:]),
                "requests": redact_sensitive_data(self.state.get("requests", [])[-200:]),
                "artifacts": redact_sensitive_data(self.state.get("artifacts", [])[-200:]),
                "browser_session_id": self.state.get("browser_session_id"),
                "done": self._done.is_set(),
                "error": self.state.get("error", ""),
            }

    def result(self) -> dict[str, Any] | None:
        return redact_sensitive_data(self._result) if self._result else None

    def _build_result(self, *, ok: bool, result: str = "", error: str = "") -> dict[str, Any]:
        output = {
            "ok": ok,
            "mission_id": self.mission_id,
            "goal": self.mission.get("goal", ""),
            "result": result,
            "findings": self.state.get("findings", []),
            "requests": self.state.get("requests", []),
            "artifacts": self.state.get("artifacts", []),
            "steps": self.state.get("step", 0),
            "requests_used": self.state.get("requests_used", 0),
            "visited_count": len(self.state.get("visited", [])),
            "checkpoint_dir": os.path.join("checkpoints", self.mission_id),
        }
        if error:
            output["error"] = error
        return cast(dict[str, Any], redact_sensitive_data(output))
