"""webspider.cli — CLI entry point for ether-webspider.

Usage:
    python -m webspider.cli run --goal "..." --start https://example.com
    python -m webspider.cli resume --checkpoint <mission_id>
    python -m webspider.cli list-checkpoints
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ether-webspider — Goal-oriented web spider agent",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ────────────────────────────────────────────────────────────────
    run_p = sub.add_parser("run", help="Start a new spider mission")
    run_p.add_argument("--goal", "-g", required=True, help="What to find (e.g. 'Encontrar el endpoint de login')")
    run_p.add_argument("--start", "-s", required=True, help="Starting URL")
    run_p.add_argument("--max-steps", "-m", type=int, default=30, help="Max agent steps (default 30)")
    run_p.add_argument("--allowed-domains", "-d", nargs="*", default=None, help="Restrict to these domains")
    run_p.add_argument("--no-search", action="store_true", help="Disable DuckDuckGo search as seed finder")
    run_p.add_argument("--mission", help="Path to JSON mission file (overrides other args)")
    run_p.add_argument("--output", "-o", default=None, help="Write report JSON to file")

    # ── resume ─────────────────────────────────────────────────────────────
    resume_p = sub.add_parser("resume", help="Resume a mission from checkpoint")
    resume_p.add_argument("--checkpoint", "-c", required=True, help="Mission ID or checkpoint path")
    resume_p.add_argument("--output", "-o", default=None, help="Write report JSON to file")

    # ── list-checkpoints ───────────────────────────────────────────────────
    list_p = sub.add_parser("list-checkpoints", help="List all mission checkpoints")
    list_p.add_argument("--dir", default="checkpoints", help="Checkpoint directory (default checkpoints/)")

    args = parser.parse_args()

    if args.command == "run":
        _cmd_run(args)
    elif args.command == "resume":
        _cmd_resume(args)
    elif args.command == "list-checkpoints":
        _cmd_list_checkpoints(args)


def _cmd_run(args: argparse.Namespace) -> None:
    from webspider.agent import run_mission
    from webspider.config import get_model
    from webspider.mcp_client import get_mcp_tools
    from webspider.mission import mission_from_args, mission_from_file

    if args.mission:
        mission = mission_from_file(args.mission)
    else:
        mission = mission_from_args(
            goal=args.goal,
            start=args.start,
            max_steps=args.max_steps,
            allowed_domains=args.allowed_domains,
            disable_search=args.no_search,
        )

    model = get_model()

    try:
        with get_mcp_tools() as tools:
            result = run_mission(mission, mcp_tools=tools, model=model)
    except Exception as e:
        print(f"Error connecting to ether-websearch MCP: {e}", file=sys.stderr)
        print("Make sure ether-websearch REST and MCP are running (`just up`).", file=sys.stderr)
        sys.exit(1)

    _print_result(result, args.output)


def _cmd_resume(args: argparse.Namespace) -> None:
    from webspider.agent import resume_mission
    from webspider.config import get_model
    from webspider.mcp_client import get_mcp_tools

    checkpoint_id = os.path.basename(args.checkpoint.rstrip("/"))

    model = get_model()

    try:
        with get_mcp_tools() as tools:
            result = resume_mission(checkpoint_id, mcp_tools=tools, model=model)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error connecting to ether-websearch MCP: {e}", file=sys.stderr)
        print("Make sure ether-websearch REST and MCP are running (`just up`).", file=sys.stderr)
        sys.exit(1)

    _print_result(result, args.output)


def _cmd_list_checkpoints(args: argparse.Namespace) -> None:
    checkpoint_dir = args.dir
    if not os.path.isdir(checkpoint_dir):
        print("No checkpoints directory found.")
        return

    missions = os.listdir(checkpoint_dir)
    if not missions:
        print("No checkpoints found.")
        return

    print(f"{'MISSION ID':<30} {'STEPS':>6} {'VISITED':>8} {'FINDINGS':>9}")
    print("-" * 56)
    for mid in sorted(missions):
        state_path = os.path.join(checkpoint_dir, mid, "state.json")
        if os.path.isfile(state_path):
            with open(state_path) as f:
                state = json.load(f)
            step = state.get("step", "?")
            visited = len(state.get("visited", []))
            findings = len(state.get("findings", []))
            print(f"{mid:<30} {str(step):>6} {visited:>8} {findings:>9}")
        else:
            print(f"{mid:<30} {'?':>6} {'?':>8} {'?':>9}")


def _print_result(result: dict, output_path: str | None) -> None:
    """Print mission result to stdout and optionally write JSON."""
    status = "OK" if result["ok"] else "FAILED"
    print(f"\nMission {result['mission_id']} — {status}")
    print(f"  Goal: {result['goal']}")
    print(f"  URLs visited: {result['visited_count']}")
    print(f"  Findings: {len(result.get('findings', []))}")
    for f in result.get("findings", []):
        print(f"    - {f.get('url', '?')} [{f.get('type', '?')}]")

    if not result["ok"]:
        print(f"  Error: {result.get('error', 'unknown')}")

    print(f"\n  Checkpoint: {result['checkpoint_dir']}")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  Report saved to: {output_path}")


if __name__ == "__main__":
    main()
