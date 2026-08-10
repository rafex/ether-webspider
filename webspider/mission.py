"""webspider.mission — Mission definition, prompt builder, and final report.

Usage:
    from webspider.mission import mission_from_args, build_prompt, build_resume_prompt

    mission = mission_from_args(
        goal="Encontrar el endpoint de login",
        start="https://example.com",
        max_steps=30,
    )
    prompt = build_prompt(mission)
"""

from __future__ import annotations

import json
from typing import Any


def mission_from_args(
    goal: str,
    start: str,
    max_steps: int = 30,
    allowed_domains: list[str] | None = None,
    disable_search: bool = False,
    discovery_mode: str = "passive",
    max_requests: int = 200,
    target_protocols: list[str] | None = None,
    replay_policy: str = "observe",
    active_confirmed: bool = False,
    context: str = "",
    interaction_mode: str = "autonomous",
    browser: dict[str, Any] | None = None,
    mutation_policy: str = "safe",
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a mission dict from CLI arguments.

    Args:
        goal: Natural language description of what to find.
        start: Starting URL for exploration.
        max_steps: Maximum agent steps before stopping.
        allowed_domains: Optional list of domains to restrict crawling to.
        disable_search: If True, the agent won't use search_duckduckgo as seed finder.

    Returns:
        Mission dict ready for the agent.
    """
    if discovery_mode not in {"passive", "probe", "active"}:
        raise ValueError("discovery_mode must be passive, probe, or active")
    if interaction_mode not in {"autonomous", "interactive", "hybrid"}:
        raise ValueError("interaction_mode must be autonomous, interactive, or hybrid")
    if mutation_policy not in {"safe", "all_authorized"}:
        raise ValueError("mutation_policy must be safe or all_authorized")
    if discovery_mode == "active" and (not allowed_domains or not active_confirmed):
        raise ValueError("active discovery requires allowed_domains and active_confirmed=true")
    if mutation_policy == "all_authorized" and (
        discovery_mode != "active" or not allowed_domains or not active_confirmed
    ):
        raise ValueError("all_authorized mutations require active discovery, allowlist and active_confirmed=true")
    if max_steps < 1 or max_requests < 1:
        raise ValueError("max_steps and max_requests must be positive")
    session_config = dict(session or {})
    if "credentials" in session_config:
        raise ValueError("Raw credentials must be supplied ephemerally, not embedded in a mission")
    browser_config = {
        "engine": "playwright",
        "browser": "chromium",
        "headed": False,
        "attach": False,
        "session_id": None,
        **(browser or {}),
    }
    if (
        browser_config.get("attach")
        and not browser_config.get("session_id")
        and not session_config.get("attach_endpoint")
    ):
        raise ValueError("attach requires browser.session_id or session.attach_endpoint")
    return {
        "goal": goal,
        "start_url": start,
        "max_steps": max_steps,
        "allowed_domains": allowed_domains or [],
        "disable_search": disable_search,
        "discovery_mode": discovery_mode,
        "max_requests": max_requests,
        "target_protocols": target_protocols or ["rest", "soap", "graphql", "grpc", "form"],
        "context": context,
        "interaction_mode": interaction_mode,
        "browser": browser_config,
        "session": session_config,
        "replay_policy": replay_policy,
        "active_confirmed": active_confirmed,
        "mutation_policy": mutation_policy,
    }


def mission_from_file(path: str) -> dict[str, Any]:
    """Load a mission from a JSON file.

    Args:
        path: Path to a JSON mission file.

    Returns:
        Mission dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    required = ("goal", "start_url")
    for key in required:
        if key not in data:
            raise ValueError(f"Mission file missing required key: {key!r}")

    session_config = dict(data.get("session", {}))
    if "credentials" in session_config:
        raise ValueError("Raw credentials must be supplied ephemerally, not embedded in a mission")
    browser_config = {
        "engine": "playwright",
        "browser": "chromium",
        "headed": False,
        "attach": False,
        "session_id": None,
        **data.get("browser", {}),
    }
    if (
        browser_config.get("attach")
        and not browser_config.get("session_id")
        and not session_config.get("attach_endpoint")
    ):
        raise ValueError("attach requires browser.session_id or session.attach_endpoint")

    mission = {
        "goal": data["goal"],
        "start_url": data["start_url"],
        "max_steps": data.get("max_steps", 30),
        "allowed_domains": data.get("allowed_domains", []),
        "disable_search": data.get("disable_search", False),
        "discovery_mode": data.get("discovery_mode", data.get("mode", "passive")),
        "max_requests": data.get("max_requests", 200),
        "target_protocols": data.get("target_protocols", ["rest", "soap", "graphql", "grpc", "form"]),
        "context": data.get("context", ""),
        "interaction_mode": data.get("interaction_mode", "autonomous"),
        "browser": browser_config,
        "session": session_config,
        "replay_policy": data.get("replay_policy", "observe"),
        "active_confirmed": data.get("active_confirmed", False),
        "mutation_policy": data.get("mutation_policy", "safe"),
    }
    if mission["discovery_mode"] not in {"passive", "probe", "active"}:
        raise ValueError("discovery_mode must be passive, probe, or active")
    if mission["interaction_mode"] not in {"autonomous", "interactive", "hybrid"}:
        raise ValueError("interaction_mode must be autonomous, interactive, or hybrid")
    if mission["mutation_policy"] not in {"safe", "all_authorized"}:
        raise ValueError("mutation_policy must be safe or all_authorized")
    if mission["discovery_mode"] == "active" and (not mission["allowed_domains"] or not mission["active_confirmed"]):
        raise ValueError("active discovery requires allowed_domains and active_confirmed=true")
    if mission["mutation_policy"] == "all_authorized" and (
        mission["discovery_mode"] != "active" or not mission["allowed_domains"] or not mission["active_confirmed"]
    ):
        raise ValueError("all_authorized mutations require active discovery, allowlist and active_confirmed=true")
    if int(mission["max_steps"]) < 1 or int(mission["max_requests"]) < 1:
        raise ValueError("max_steps and max_requests must be positive")
    return mission


def build_prompt(mission: dict[str, Any]) -> str:
    """Build the initial agent prompt for a mission.

    Args:
        mission: Mission dict from mission_from_args or mission_from_file.

    Returns:
        Prompt string for the CodeAgent.
    """
    domain_hint = ""
    if mission["allowed_domains"]:
        domain_hint = f"\nOnly crawl within these domains: {', '.join(mission['allowed_domains'])}."

    search_hint = ""
    if not mission["disable_search"]:
        search_hint = "\nYou can use `search_duckduckgo` to find the starting point if needed."

    max_steps = mission["max_steps"]

    mode = mission.get("discovery_mode", "passive")
    interaction_mode = mission.get("interaction_mode", "autonomous")
    protocols = ", ".join(mission.get("target_protocols", []))
    probe_enabled = str(mode in {"probe", "active"}).lower()
    active_guard = (
        "Active actions are authorized only because active_confirmed=true and the allowlist is present."
        if mode == "active"
        else "Do not replay or submit mutating requests in this mission."
    )

    return f"""You are WebSpider, an endpoint-discovery agent. Your mission:

GOAL: {mission["goal"]}
START URL: {mission["start_url"]}{domain_hint}{search_hint}
DISCOVERY MODE: {mode}
INTERACTION MODE: {interaction_mode}
CONTEXT: {mission.get("context", "")}
TARGET PROTOCOLS: {protocols}
MAX REQUESTS: {mission.get("max_requests", 200)}
REPLAY POLICY: {mission.get("replay_policy", "observe")}
{active_guard}
MUTATION POLICY: {mission.get("mutation_policy", "safe")}

You have these web tools available:
- fetch_capabilities() — inspect the tools actually registered in this run
- spider_webpage(url, depth, max_pages, classify=true, probe={probe_enabled}, ...) — bounded crawl and classification
- capture_browser_network(url, ...) — render dynamic pages and capture navigation/XHR/fetch/form requests
- extract_api_artifacts(url, content, ...) — inspect HTML, JavaScript, JSON, OpenAPI, WSDL, GraphQL and proto artifacts
- inspect_http_endpoint(url, ...) — safe HEAD/OPTIONS/GET observations
- inspect_grpc_endpoint(url, ...) — detect gRPC/gRPC-Web and inspect descriptors
- browser_session(url, ...) — use supplied storage state or guided login recipe; secrets stay in memory
- browser_session_start(...) — start or attach a persistent visible browser
- browser_session_command(...) — navigate, click, fill, wait, or transfer browser control
- browser_session_status/events(...) — inspect current browser and captured network events
- get_session_credentials() — obtain explicitly supplied runtime credentials only for an authorized login flow
- replay_request(...) — only when the mission mode and allowlist authorize it
- crawl_webpage(url, mode="markdown", ...) — extract LLM-ready markdown via crawl4ai
- fetch_webpage(url, ...) — fetch a single page and extract clean text
- fetch_browser(url, ...) — render JavaScript-heavy pages
- search_duckduckgo(query, ...) — search the web
- search_news(query, ...) — search news
- navigate_webpage(url, ...) — interactive navigation with recipes
- scrape_social_media(platform, query, ...) — search social media

STATE TOOLS (use these to track your progress):
- record_endpoint_finding(finding) — record the structured endpoint/request schema
- record_request(request) — deduplicate by method + normalized URL + body hash and create a finding
- record_artifact(artifact) — store OpenAPI/WSDL/GraphQL/proto evidence
- add_finding(url, type, confidence, notes) — legacy compatibility for simple findings
- mark_visited(url) — mark a URL as already explored
- add_to_frontier(url, priority, reason) — add a URL to the exploration queue with priority 0.0-1.0
- state_summary() — get a JSON summary of current state (visited, frontier, findings)
- save_checkpoint(reason) — persist current state to disk for resume
- load_checkpoint() — restore state from the last checkpoint
- request_capability(name, description, use_case) — request a missing tool from ether-websearch

STRATEGY:
1. Call `fetch_capabilities()` and fail explicitly if a required capability is missing.
2. Call `spider_webpage` on START URL with classify=true, probe={probe_enabled} and the allowlist. Call `mark_visited`.
3. For every HTML/JS page, call `extract_api_artifacts`; use `capture_browser_network` for dynamic pages, forms, or authenticated flows.
4. For every captured request/artifact, call `record_request`, `record_artifact`, or `record_endpoint_finding` with method, query, headers redacted, body, response, source and evidence.
5. For each promising internal link, call `add_to_frontier` with a priority score:
   - 0.9-1.0: URL or text strongly matches the goal
   - 0.5-0.8: moderately relevant
   - 0.1-0.4: possibly relevant
6. After every tool call, save/checkpoint state; never write credentials, cookies, Authorization headers or storage state.
7. Use probes automatically only in probe/active mode. Replay, login submission and POST/PUT/PATCH/DELETE require active mode, allowlist and explicit mission authorization.
8. Use `state_summary()` to pick the next unvisited URL/request and continue until the goal is found OR {max_steps} steps are reached.
9. Check `get_user_instruction()` after each checkpoint. Apply it to the next action without exposing secrets in observations.
10. In interactive mode, wait for a user instruction before taking the next action. In hybrid mode, honor takeover/pause immediately.

REPORT:
When finished, print a summary with:
- Goal achieved: YES/NO
- Findings: endpoint, protocol, method, request/response, evidence and confidence
- Requests: captured request count and coverage by source/protocol
- Steps taken: total
- URLs visited: count

Limit your exploration to {max_steps} steps and {mission.get("max_requests", 200)} requests maximum.
"""


def build_resume_prompt(mission: dict[str, Any], state: dict) -> str:
    """Build a resume prompt for continuing a mission from a checkpoint.

    Args:
        mission: Mission dict.
        state: Checkpoint state (loaded from state.json).

    Returns:
        Prompt string for the CodeAgent.
    """
    step = state.get("step", 0)
    visited_count = len(state.get("visited", []))
    frontier_count = len(state.get("frontier", []))
    findings_count = len(state.get("findings", []))
    requests_count = len(state.get("requests", []))

    findings_summary = ""
    if state.get("findings"):
        findings_summary = "\nFindings so far:\n"
        for f in state["findings"][-10:]:
            findings_summary += f"  - {f.get('endpoint', f.get('url', '?'))} [{f.get('protocol', f.get('type', '?'))}] {f.get('method', 'GET')}\n"

    frontier_prioritized = ""
    if state.get("frontier"):
        frontier_prioritized = "\nTop priority URLs still to explore:\n"
        sorted_frontier = sorted(
            state["frontier"],
            key=lambda x: x.get("priority", 0),
            reverse=True,
        )
        for f in sorted_frontier[:5]:
            frontier_prioritized += f"  - {f.get('url', '?')} (priority: {f.get('priority', 0):.2f})\n"

    return f"""You are resuming a web spider mission from step {step}.

ORIGINAL GOAL: {mission["goal"]}
START URL: {mission["start_url"]}
MAX STEPS: {mission["max_steps"]}

Current state: {visited_count} visited, {findings_count} findings, {requests_count} requests, {frontier_count} in frontier.
{findings_summary}{frontier_prioritized}
Call `load_checkpoint()` first to restore state. Then use `state_summary()` to review
and pick the highest-priority URL from the frontier to explore next.
Use `mark_visited`, `add_to_frontier`, `record_request`, `record_endpoint_finding`, and `save_checkpoint` as you explore.
If the goal is already found, report it.

Limit remaining steps to {max(0, mission["max_steps"] - step)} and remaining requests to {max(0, mission.get("max_requests", 200) - requests_count)}.
"""
