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
    return {
        "goal": goal,
        "start_url": start,
        "max_steps": max_steps,
        "allowed_domains": allowed_domains or [],
        "disable_search": disable_search,
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

    return {
        "goal": data["goal"],
        "start_url": data["start_url"],
        "max_steps": data.get("max_steps", 30),
        "allowed_domains": data.get("allowed_domains", []),
        "disable_search": data.get("disable_search", False),
    }


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

    return f"""You are a web spider agent. Your mission:

GOAL: {mission["goal"]}
START URL: {mission["start_url"]}{domain_hint}{search_hint}

You have these web tools available:
- spider_webpage(url, depth, max_pages, ...) — deep crawl with endpoint classification (login, SOAP, REST, ASP, JSP, PHP, forms)
- crawl_webpage(url, mode="markdown", ...) — extract LLM-ready markdown via crawl4ai
- fetch_webpage(url, ...) — fetch a single page and extract clean text
- fetch_browser(url, ...) — render JavaScript-heavy pages
- search_duckduckgo(query, ...) — search the web
- search_news(query, ...) — search news
- navigate_webpage(url, ...) — interactive navigation with recipes
- scrape_social_media(platform, query, ...) — search social media

STATE TOOLS (use these to track your progress):
- add_finding(url, type, confidence, notes) — record a discovery (login, api, rest, soap, form, etc.)
- mark_visited(url) — mark a URL as already explored
- add_to_frontier(url, priority, reason) — add a URL to the exploration queue with priority 0.0-1.0
- state_summary() — get a JSON summary of current state (visited, frontier, findings)
- save_checkpoint(reason) — persist current state to disk for resume
- load_checkpoint() — restore state from the last checkpoint
- request_capability(name, description, use_case) — request a missing tool from ether-websearch

STRATEGY:
1. Start by calling `spider_webpage` on the START URL with depth=1. Call `mark_visited`.
2. Examine the results: links found, endpoints discovered, page content.
3. For each finding that seems relevant to the GOAL, call `add_finding`.
4. For each promising internal link, call `add_to_frontier` with a priority score:
   - 0.9-1.0: URL or text strongly matches the goal
   - 0.5-0.8: moderately relevant
   - 0.1-0.4: possibly relevant
5. After exploring each URL, call `save_checkpoint` with a brief reason.
6. Use `state_summary()` to check your progress and pick the next URL to explore.
7. Continue until the goal is found OR {max_steps} steps are reached.

REPORT:
When finished, print a summary with:
- Goal achieved: YES/NO
- Findings: list of discovered URLs with their type and relevance
- Steps taken: total
- URLs visited: count

Limit your exploration to {max_steps} steps maximum.
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

    findings_summary = ""
    if state.get("findings"):
        findings_summary = "\nFindings so far:\n"
        for f in state["findings"][-10:]:
            findings_summary += f"  - {f.get('url', '?')} [{f.get('type', '?')}]\n"

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

Current state: {visited_count} visited, {findings_count} findings, {frontier_count} in frontier.
{findings_summary}{frontier_prioritized}
Call `load_checkpoint()` first to restore state. Then use `state_summary()` to review
and pick the highest-priority URL from the frontier to explore next.
Use `mark_visited`, `add_to_frontier`, `add_finding`, and `save_checkpoint` as you explore.
If the goal is already found, report it.

Limit remaining steps to {mission["max_steps"] - step}.
"""
