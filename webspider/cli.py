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
    run_p.add_argument(
        "--mode", choices=("passive", "probe", "active"), default="passive", help="Endpoint discovery mode"
    )
    run_p.add_argument("--max-requests", type=int, default=200, help="Global captured/probed request limit")
    run_p.add_argument("--target-protocols", nargs="*", default=None, help="Protocols to prioritize")
    run_p.add_argument("--confirm-active", action="store_true", help="Explicitly authorize active exploration")
    run_p.add_argument("--interaction-mode", choices=("autonomous", "interactive", "hybrid"), default="autonomous")
    run_p.add_argument("--browser", choices=("chromium", "chrome", "firefox", "webkit", "safari"), default="chromium")
    run_p.add_argument("--headed", action="store_true", help="Show the browser window")
    run_p.add_argument("--attach", action="store_true", help="Attach to an existing browser when supported")
    run_p.add_argument("--attach-endpoint", default=None, help="Chromium CDP endpoint for attach mode")
    run_p.add_argument("--session-id", default=None, help="Reuse or assign a persistent browser session id")
    run_p.add_argument("--context", default="", help="Additional mission context")
    run_p.add_argument("--mutation-policy", choices=("safe", "all_authorized"), default="safe")
    run_p.add_argument("--credential-ref", default=None, help="Keychain/encrypted-store credential reference")
    run_p.add_argument("--credentials-stdin", action="store_true", help="Read ephemeral credential JSON from stdin")
    run_p.add_argument("--storage-state", default=None, help="User-provided Playwright storage state path")
    run_p.add_argument("--no-search", action="store_true", help="Disable DuckDuckGo search as seed finder")
    run_p.add_argument("--mission", help="Path to JSON mission file (overrides other args)")
    run_p.add_argument("--output", "-o", default=None, help="Write report JSON to file")

    # ── resume ─────────────────────────────────────────────────────────────
    resume_p = sub.add_parser("resume", help="Resume a mission from checkpoint")
    resume_p.add_argument("--checkpoint", "-c", required=True, help="Mission ID or checkpoint path")
    resume_p.add_argument("--output", "-o", default=None, help="Write report JSON to file")
    resume_p.add_argument("--credentials-stdin", action="store_true", help="Read ephemeral credential JSON from stdin")

    # ── serve / chat ───────────────────────────────────────────────────────
    serve_p = sub.add_parser("serve", help="Start the local Web UI and WebSocket control plane")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8787)
    serve_p.add_argument("--no-mcp", action="store_true", help="Start UI without connecting to ether-websearch")

    chat_p = sub.add_parser("chat", help="Open a terminal chat for a running mission")
    chat_p.add_argument("--mission", "-m", required=True, help="Mission id")
    chat_p.add_argument("--base-url", default=None, help="WebSpider UI URL")

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
    elif args.command == "serve":
        _cmd_serve(args)
    elif args.command == "chat":
        _cmd_chat(args)


def _cmd_run(args: argparse.Namespace) -> None:
    from webspider.agent import run_mission
    from webspider.config import get_model
    from webspider.mcp_client import get_mcp_tools
    from webspider.mission import mission_from_args, mission_from_file

    if args.mission:
        mission = mission_from_file(args.mission)
        credentials: dict[str, str] = {}
    else:
        credentials = json.load(sys.stdin) if args.credentials_stdin else {}
        mission = mission_from_args(
            goal=args.goal,
            start=args.start,
            max_steps=args.max_steps,
            allowed_domains=args.allowed_domains,
            disable_search=args.no_search,
            discovery_mode=args.mode,
            max_requests=args.max_requests,
            target_protocols=args.target_protocols,
            active_confirmed=args.confirm_active,
            context=args.context,
            interaction_mode=args.interaction_mode,
            browser={
                "browser": args.browser,
                "headed": args.headed,
                "attach": args.attach,
                "session_id": args.session_id,
                "engine": "selenium" if args.browser == "safari" else "playwright",
            },
            mutation_policy=args.mutation_policy,
            session={
                "credential_ref": args.credential_ref,
                "storage_state_path": args.storage_state,
                "attach_endpoint": args.attach_endpoint,
            },
        )

    model = get_model()

    try:
        with get_mcp_tools() as tools:
            result = run_mission(mission, mcp_tools=tools, model=model, credentials=credentials)
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
    credentials = json.load(sys.stdin) if args.credentials_stdin else {}

    try:
        with get_mcp_tools() as tools:
            result = resume_mission(checkpoint_id, mcp_tools=tools, model=model, credentials=credentials)
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
        endpoint = f.get("endpoint", f.get("url", "?"))
        protocol = f.get("protocol", f.get("type", "?"))
        method = f.get("method", "GET")
        print(f"    - {method} {endpoint} [{protocol}]")

    if not result["ok"]:
        print(f"  Error: {result.get('error', 'unknown')}")

    print(f"\n  Checkpoint: {result['checkpoint_dir']}")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  Report saved to: {output_path}")


def _cmd_serve(args: argparse.Namespace) -> None:
    """Run the Web UI while keeping the MCP stdio context alive."""
    import uvicorn

    from webspider.server import app, configure_runtime

    if args.host not in {"127.0.0.1", "localhost", "::1"} and not os.environ.get("WEBSPIDER_UI_TOKEN"):
        print("Refusing non-local Web UI without WEBSPIDER_UI_TOKEN", file=sys.stderr)
        sys.exit(2)

    if args.no_mcp:
        configure_runtime()
        uvicorn.run(app, host=args.host, port=args.port)
        return

    from webspider.config import get_model
    from webspider.mcp_client import get_mcp_tools

    try:
        with get_mcp_tools() as tools:
            configure_runtime(tools, get_model())
            uvicorn.run(app, host=args.host, port=args.port)
    except Exception as exc:
        print(f"Error starting WebSpider UI: {exc}", file=sys.stderr)
        sys.exit(1)


def _cmd_chat(args: argparse.Namespace) -> None:
    """Small terminal client backed by the same Web UI REST control plane."""
    import urllib.error
    import urllib.request

    base_url = (args.base_url or os.environ.get("WEBSPIDER_UI_BASE_URL", "http://127.0.0.1:8787")).rstrip("/")
    token = os.environ.get("WEBSPIDER_UI_TOKEN", "")

    def request(path: str, method: str = "GET", body: dict | None = None) -> dict:
        headers = {"Accept": "application/json"}
        if token:
            headers["X-WebSpider-Token"] = token
        payload = json.dumps(body).encode() if body is not None else None
        if payload:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{base_url}{path}", data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return dict(json.loads(response.read().decode()))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"WebSpider UI unavailable at {base_url}: {exc}") from exc

    print(f"WebSpider chat — mission {args.mission}. Commands: /pause /resume /takeover /release /stop /status /quit")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            continue
        if text in {"/quit", "/exit"}:
            return
        if text.startswith("/"):
            action = text[1:].split(maxsplit=1)[0]
            if action == "status":
                print(json.dumps(request(f"/api/missions/{args.mission}"), indent=2, ensure_ascii=False))
            else:
                print(
                    json.dumps(
                        request(f"/api/missions/{args.mission}/control", "POST", {"action": action}),
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            continue
        result = request(f"/api/missions/{args.mission}/messages", "POST", {"text": text})
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
