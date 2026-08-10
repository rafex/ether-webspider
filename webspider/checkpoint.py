"""webspider.checkpoint — Mission state persistence and resume.

Checkpoints are stored as JSON files under ``checkpoints/<mission_id>/``:
    state.json   — mission definition, visited URLs, frontier, findings, step count.
    memory.jsonl — serialized agent memory steps (one JSON object per line).

Usage:
    from webspider.checkpoint import (
        save_checkpoint, load_checkpoint, create_step_callback,
        create_state_tools,
    )

    # As a utility
    state = load_checkpoint("my_mission")
    callback = create_step_callback("my_mission", agent.memory.steps)

    # State tools for the agent
    tools = create_state_tools(mission_id, state_ref)
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.parse
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, cast

_SECRET_KEY_RE = re.compile(
    r"(?:authorization|cookie|set-cookie|password|passwd|secret|token|api[_-]?key|storage[_-]?state)", re.I
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_ASSIGNMENT_RE = re.compile(r"(?i)(\b(?:password|passwd|secret|token|api[_-]?key)\s*[=:]\s*)([^,\s;&]+)")


def _redact_value(value: Any, key: str = "") -> Any:
    """Recursively remove credentials before state, memory, or report writes."""
    if _SECRET_KEY_RE.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): _redact_value(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return _SECRET_ASSIGNMENT_RE.sub(r"\1[REDACTED]", _BEARER_RE.sub("Bearer [REDACTED]", value))
    return value


def redact_sensitive_data(value: Any) -> Any:
    """Return a redacted copy suitable for reports and API responses."""
    return _redact_value(value)


def _url_allowed(state_ref: dict, url: str) -> bool:
    domains = state_ref.get("mission", {}).get("allowed_domains", [])
    if not domains:
        return True
    host = (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")
    return any(
        host == domain.lower().lstrip(".") or host.endswith("." + domain.lower().lstrip(".")) for domain in domains
    )


def _request_key(request: dict[str, Any]) -> str:
    url = str(request.get("url") or request.get("endpoint") or "")
    parsed = urllib.parse.urlsplit(url)
    normalized = urllib.parse.urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))),
            "",
        )
    )
    body = request.get("body")
    body_json = json.dumps(body, sort_keys=True, ensure_ascii=False, default=str)
    return f"{str(request.get('method', 'GET')).upper()} {normalized} {sha256(body_json.encode()).hexdigest()}"


def _checkpoints_base() -> str:
    return os.environ.get("WEBSPIDER_CHECKPOINTS", "checkpoints")


def _mission_dir(mission_id: str) -> str:
    return os.path.join(_checkpoints_base(), mission_id)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_checkpoint(mission_id: str, state: dict) -> str:
    """Persist mission state to disk.

    Args:
        mission_id: Unique identifier for this mission.
        state: Dict with keys: mission, step, visited, frontier, findings.

    Returns:
        Path to the saved state file.
    """
    d = _mission_dir(mission_id)
    _ensure_dir(d)

    safe_state = _redact_value(dict(state))
    safe_state["last_step_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_state["mission_id"] = mission_id

    state_path = os.path.join(d, "state.json")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=d, delete=False) as f:
        json.dump(safe_state, f, ensure_ascii=False, indent=2)
        temp_path = f.name
    os.replace(temp_path, state_path)

    return state_path


def load_checkpoint(mission_id: str) -> dict | None:
    """Load mission state from disk.

    Args:
        mission_id: Unique identifier for the mission.

    Returns:
        State dict or None if the checkpoint does not exist.
    """
    state_path = os.path.join(_mission_dir(mission_id), "state.json")
    if not os.path.isfile(state_path):
        return None

    with open(state_path, encoding="utf-8") as f:
        return cast(dict, json.load(f))


def save_memory(mission_id: str, memory_steps: list) -> str:
    """Serialize agent memory steps to JSONL.

    Uses step.dict() (smolagents MemoryStep API) and falls back to repr.

    Args:
        mission_id: Unique identifier for this mission.
        memory_steps: List of smolagents memory step objects (with .dict()).

    Returns:
        Path to the saved memory file.
    """
    d = _mission_dir(mission_id)
    _ensure_dir(d)

    memory_path = os.path.join(d, "memory.jsonl")
    with open(memory_path, "w", encoding="utf-8") as f:
        for step in memory_steps:
            try:
                if hasattr(step, "dict"):
                    step_dict = step.dict()
                elif isinstance(step, dict):
                    step_dict = step
                else:
                    step_dict = {"step_type": type(step).__name__, "repr": repr(step)}
                f.write(json.dumps(_redact_value(step_dict), ensure_ascii=False, default=str) + "\n")
            except Exception:
                f.write(json.dumps({"error": "serialization_failed", "step_type": type(step).__name__}) + "\n")

    return memory_path


def load_memory(mission_id: str) -> list[dict]:
    """Load serialized memory steps from JSONL.

    Args:
        mission_id: Unique identifier for the mission.

    Returns:
        List of step dicts.
    """
    memory_path = os.path.join(_mission_dir(mission_id), "memory.jsonl")
    if not os.path.isfile(memory_path):
        return []

    steps = []
    with open(memory_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    steps.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return steps


def create_step_callback(mission_id: str, state_ref: dict | None = None) -> Callable:
    """Create a step callback that persists memory after each agent step.

    smolagents calls step callbacks as ``callback(memory_step, agent=self)``
    (see agents.py:_finalize_step). We use the ``agent`` kwarg to access
    ``agent.memory.steps`` directly.

    Args:
        mission_id: Unique identifier for the mission.

    Returns:
        A callable suitable for use as a step callback.
    """

    def _on_step(memory_step: Any = None, agent: Any = None) -> None:
        if state_ref is not None:
            state_ref["step"] = int(state_ref.get("step", 0)) + 1
            state_ref["tool_calls"] = int(state_ref.get("tool_calls", 0)) + 1
        if agent is not None and hasattr(agent, "memory") and agent.memory.steps:
            save_memory(mission_id, agent.memory.steps)
        if state_ref is not None:
            save_checkpoint(mission_id, state_ref)

    return _on_step


# ── State tools for the agent ──────────────────────────────────────────────────


def create_state_tools(mission_id: str, state_ref: dict, on_finding: Callable | None = None) -> dict[str, Callable]:
    """Create the full set of state management tools for the agent.

    Tools mutate the shared ``state_ref`` dict so the agent can track
    visited URLs, the frontier, and findings across steps.

    Args:
        mission_id: Unique identifier for the mission.
        state_ref: Mutable dict (mission, step, visited, frontier, findings).

    Returns:
        Dict of tool_name → callable.
    """
    return {
        "add_finding": _create_add_finding(state_ref, on_finding),
        "record_endpoint_finding": _create_record_endpoint_finding(state_ref, on_finding),
        "record_request": _create_record_request(state_ref, on_finding),
        "record_artifact": _create_record_artifact(state_ref),
        "get_user_instruction": _create_get_user_instruction(state_ref),
        "get_session_credentials": _create_get_session_credentials(state_ref),
        "mark_visited": _create_mark_visited(state_ref),
        "add_to_frontier": _create_add_to_frontier(state_ref),
        "state_summary": _create_state_summary(state_ref),
        "save_checkpoint": _create_save_checkpoint(mission_id, state_ref),
        "load_checkpoint": _create_load_checkpoint(mission_id, state_ref),
    }


def _create_add_finding(state_ref: dict, on_finding: Callable | None = None) -> Callable:
    def _add_finding(url: str, finding_type: str = "unknown", confidence: float = 0.5, notes: str = "") -> str:
        """Register a discovered finding."""
        for f in state_ref.get("findings", []):
            if f.get("url") == url:
                f.update(type=finding_type, confidence=confidence, notes=notes)
                if on_finding:
                    on_finding(f)
                return f"Updated finding: {url} [{finding_type}]"

        finding = {"url": url, "type": finding_type, "confidence": confidence, "notes": notes}
        state_ref.setdefault("findings", []).append(finding)
        if on_finding:
            on_finding(finding)
        return f"Finding added: {url} [{finding_type}]"

    return _add_finding


def _create_record_endpoint_finding(state_ref: dict, on_finding: Callable | None = None) -> Callable:
    def _record_endpoint_finding(finding: dict[str, Any]) -> str:
        """Register a structured endpoint finding and merge repeated evidence."""
        endpoint = str(finding.get("endpoint") or finding.get("url") or "")
        if not endpoint or not _url_allowed(state_ref, endpoint):
            return "Finding rejected: endpoint is empty or outside allowed_domains."
        normalized = dict(finding)
        normalized["endpoint"] = endpoint
        normalized.setdefault("protocol", normalized.get("type", "unknown"))
        normalized.setdefault("method", "GET")
        normalized.setdefault("request", {})
        normalized.setdefault("response", {})
        normalized.setdefault("evidence", [])
        normalized.setdefault("confidence", 0.5)
        normalized.setdefault("notes", "")
        normalized["url"] = endpoint
        key = f"{normalized['method'].upper()} {endpoint} {sha256(json.dumps(normalized.get('request', {}).get('body'), sort_keys=True, default=str).encode()).hexdigest()}"
        for existing in state_ref.setdefault("findings", []):
            existing_key = f"{str(existing.get('method', 'GET')).upper()} {existing.get('endpoint', existing.get('url', ''))} {sha256(json.dumps(existing.get('request', {}).get('body'), sort_keys=True, default=str).encode()).hexdigest()}"
            if existing_key == key:
                existing.update(normalized)
                existing["evidence"] = sorted(set(existing.get("evidence", [])) | set(normalized.get("evidence", [])))
                if on_finding:
                    on_finding(existing)
                return f"Updated endpoint finding: {endpoint} [{normalized['protocol']}]"
        state_ref["findings"].append(normalized)
        if on_finding:
            on_finding(normalized)
        return f"Endpoint finding added: {endpoint} [{normalized['protocol']}]"

    return _record_endpoint_finding


def _create_record_request(state_ref: dict, on_finding: Callable | None = None) -> Callable:
    def _record_request(request: dict[str, Any]) -> str:
        """Record a captured request once, enforcing mission request limits."""
        url = str(request.get("url") or request.get("endpoint") or "")
        if not url or not _url_allowed(state_ref, url):
            return "Request rejected: URL is empty or outside allowed_domains."
        limit = int(state_ref.get("mission", {}).get("max_requests", 200))
        key = _request_key(request)
        for existing in state_ref.setdefault("requests", []):
            if existing.get("dedupe_key") == key:
                return f"Request already captured: {url}"
        if len(state_ref["requests"]) >= limit:
            return f"Request limit reached: {limit}"
        stored = dict(request)
        stored["url"] = url
        stored["method"] = str(stored.get("method", "GET")).upper()
        stored["dedupe_key"] = key
        state_ref["requests"].append(stored)
        state_ref["requests_used"] = len(state_ref["requests"])
        finding = {
            "endpoint": url,
            "protocol": stored.get("protocol", "rest"),
            "method": stored["method"],
            "source_url": stored.get("source_url", ""),
            "request": stored,
            "response": stored.get("response", {}),
            "evidence": [stored.get("source", "request_capture")],
            "confidence": float(stored.get("confidence", 0.9)),
            "notes": stored.get("notes", ""),
        }
        _create_record_endpoint_finding(state_ref, on_finding)(finding)
        return f"Request recorded: {stored['method']} {url}"

    return _record_request


def _create_record_artifact(state_ref: dict) -> Callable:
    def _record_artifact(artifact: dict[str, Any]) -> str:
        """Store an API artifact while removing exact duplicates."""
        artifacts = state_ref.setdefault("artifacts", [])
        key = (artifact.get("endpoint"), artifact.get("protocol"), artifact.get("method", "GET"))
        if not any(
            (item.get("endpoint"), item.get("protocol"), item.get("method", "GET")) == key for item in artifacts
        ):
            artifacts.append(dict(artifact))
        return f"Artifact recorded: {artifact.get('endpoint', '?')}"

    return _record_artifact


def _create_get_user_instruction(state_ref: dict) -> Callable:
    def _get_user_instruction() -> str:
        """Return and consume the next non-secret user instruction."""
        instructions = state_ref.setdefault("user_instructions", [])
        if not instructions:
            return "No new user instruction. Continue the mission strategy."
        item = instructions.pop(0)
        return str(item.get("text", item))[:20_000] if isinstance(item, dict) else str(item)[:20_000]

    return _get_user_instruction


def _create_get_session_credentials(state_ref: dict) -> Callable:
    def _get_session_credentials() -> str:
        """Return runtime-only credentials for an explicitly authorized login flow."""
        return json.dumps(state_ref.get("runtime_credentials", {}), ensure_ascii=False)

    return _get_session_credentials


def _create_mark_visited(state_ref: dict) -> Callable:
    def _mark_visited(url: str) -> str:
        """Mark a URL as visited (no-op if already visited)."""
        if not _url_allowed(state_ref, url):
            return f"Rejected outside allowed_domains: {url}"
        visited = state_ref.setdefault("visited", [])
        if url not in visited:
            visited.append(url)
            state_ref["frontier"] = [item for item in state_ref.get("frontier", []) if item.get("url") != url]
            return f"Marked visited: {url}"
        return f"Already visited: {url}"

    return _mark_visited


def _create_add_to_frontier(state_ref: dict) -> Callable:
    def _add_to_frontier(url: str, priority: float = 0.5, reason: str = "") -> str:
        """Add a URL to the exploration frontier with a priority score."""
        if not _url_allowed(state_ref, url):
            return f"Rejected outside allowed_domains: {url}"
        if url in state_ref.get("visited", []):
            return f"Already visited: {url}"
        priority = max(0.0, min(1.0, priority))
        frontier = state_ref.setdefault("frontier", [])
        for item in frontier:
            if item.get("url") == url:
                item["priority"] = max(item.get("priority", 0), priority)
                item["reason"] = reason or item.get("reason", "")
                return f"Updated frontier priority for {url}"

        frontier.append({"url": url, "priority": priority, "reason": reason})
        return f"Added to frontier: {url} (priority {priority:.2f})"

    return _add_to_frontier


def _create_state_summary(state_ref: dict) -> Callable:
    def _state_summary() -> str:
        """Return a compact JSON summary of current exploration state."""
        summary = {
            "step": state_ref.get("step", 0),
            "visited_count": len(state_ref.get("visited", [])),
            "frontier_count": len(state_ref.get("frontier", [])),
            "findings_count": len(state_ref.get("findings", [])),
            "requests_count": len(state_ref.get("requests", [])),
            "artifacts_count": len(state_ref.get("artifacts", [])),
            "requests_used": state_ref.get("requests_used", 0),
            "control": state_ref.get("control", "running"),
            "top_findings": state_ref.get("findings", [])[-5:],
            "top_frontier": sorted(state_ref.get("frontier", []), key=lambda x: x.get("priority", 0), reverse=True)[:5],
        }
        return json.dumps(summary, ensure_ascii=False, indent=2)

    return _state_summary


def _create_save_checkpoint(mission_id: str, state_ref: dict) -> Callable:
    def _save_checkpoint(reason: str = "") -> str:
        """Save current mission state to checkpoint."""
        state_ref["checkpoint_reason"] = reason
        path = save_checkpoint(mission_id, dict(state_ref))
        return f"Checkpoint saved to {path}"

    return _save_checkpoint


def _create_load_checkpoint(mission_id: str, state_ref: dict) -> Callable:
    def _load_checkpoint() -> str:
        """Load mission state from the last checkpoint."""
        loaded = load_checkpoint(mission_id)
        if loaded is None:
            return "No checkpoint found."

        _excluded = ("mission_id", "last_step_at", "checkpoint_reason")
        for key, value in loaded.items():
            if key not in _excluded:
                state_ref[key] = value
        return (
            f"Checkpoint loaded: step {loaded.get('step', 0)}, "
            f"{len(loaded.get('visited', []))} visited, "
            f"{len(loaded.get('findings', []))} findings."
        )

    return _load_checkpoint
