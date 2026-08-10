"""Local Web UI and WebSocket control plane for WebSpider missions."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from webspider.mission import mission_from_args
from webspider.supervisor import MissionSupervisor


class MissionStart(BaseModel):
    goal: str = Field(..., min_length=1, max_length=20_000)
    start_url: str = Field(..., min_length=1, max_length=2_048)
    context: str = Field(default="", max_length=50_000)
    interaction_mode: str = Field(default="autonomous", pattern="^(autonomous|interactive|hybrid)$")
    discovery_mode: str = Field(default="passive", pattern="^(passive|probe|active)$")
    allowed_domains: list[str] = Field(default_factory=list)
    max_steps: int = Field(default=30, ge=1, le=10_000)
    max_requests: int = Field(default=200, ge=1, le=100_000)
    target_protocols: list[str] = Field(default_factory=list)
    active_confirmed: bool = False
    mutation_policy: str = Field(default="safe", pattern="^(safe|all_authorized)$")
    browser: dict[str, Any] = Field(default_factory=dict)
    session: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, str] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    text: str = Field(..., min_length=1, max_length=20_000)


class ControlMessage(BaseModel):
    action: str = Field(..., pattern="^(pause|resume|takeover|release|stop)$")


class MissionRegistry:
    def __init__(self) -> None:
        self._missions: dict[str, MissionSupervisor] = {}
        self.mcp_tools: list | None = None
        self.model: Any = None

    def configure(self, mcp_tools: list | None = None, model: Any = None) -> None:
        self.mcp_tools = mcp_tools
        self.model = model

    def start(self, payload: MissionStart) -> dict[str, Any]:
        mission = mission_from_args(
            goal=payload.goal,
            start=payload.start_url,
            max_steps=payload.max_steps,
            allowed_domains=payload.allowed_domains,
            discovery_mode=payload.discovery_mode,
            max_requests=payload.max_requests,
            target_protocols=payload.target_protocols or None,
            context=payload.context,
            interaction_mode=payload.interaction_mode,
            browser=payload.browser,
            session=payload.session,
            active_confirmed=payload.active_confirmed,
            mutation_policy=payload.mutation_policy,
        )
        supervisor = MissionSupervisor(
            mission,
            mcp_tools=self.mcp_tools,
            model=self.model,
            credentials=payload.credentials,
        )
        self._missions[supervisor.mission_id] = supervisor
        return supervisor.start()

    def get(self, mission_id: str) -> MissionSupervisor:
        try:
            return self._missions[mission_id]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown mission: {mission_id}") from exc

    def list(self) -> list[dict[str, Any]]:
        return [item.status() for item in self._missions.values()]


registry = MissionRegistry()
app = FastAPI(title="WebSpider Control Plane", version="0.2.0")


def _origin_allowed(origin: str | None, base_url: str = "") -> bool:
    if not origin:
        return True
    allowed = {value.strip() for value in os.environ.get("WEBSPIDER_UI_ORIGINS", "").split(",") if value.strip()}
    return bool(origin in allowed or (base_url and origin == base_url.rstrip("/")))


@app.middleware("http")
async def ui_origin_guard(request, call_next):
    """Reject cross-origin state-changing UI requests unless explicitly allowed."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/missions"):
        origin = request.headers.get("origin")
        if not _origin_allowed(origin, str(request.base_url)):
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Origin is not allowed"}, status_code=403)
    return await call_next(request)


def _authorized(token: str | None) -> bool:
    expected = os.environ.get("WEBSPIDER_UI_TOKEN", "")
    return not expected or token == expected


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _UI_HTML


@app.get("/api/missions")
async def list_missions(x_webspider_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _authorized(x_webspider_token):
        raise HTTPException(status_code=401, detail="Invalid WebSpider UI token")
    return {"missions": await run_in_threadpool(registry.list)}


@app.post("/api/missions")
async def start_mission(payload: MissionStart, x_webspider_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _authorized(x_webspider_token):
        raise HTTPException(status_code=401, detail="Invalid WebSpider UI token")
    try:
        return await run_in_threadpool(registry.start, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/missions/{mission_id}")
async def mission_status(mission_id: str, x_webspider_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _authorized(x_webspider_token):
        raise HTTPException(status_code=401, detail="Invalid WebSpider UI token")
    return await run_in_threadpool(registry.get(mission_id).status)


@app.post("/api/missions/{mission_id}/messages")
async def mission_message(
    mission_id: str,
    payload: ChatMessage,
    x_webspider_token: str | None = Header(default=None),
) -> dict[str, Any]:
    if not _authorized(x_webspider_token):
        raise HTTPException(status_code=401, detail="Invalid WebSpider UI token")
    return await run_in_threadpool(registry.get(mission_id).send_message, payload.text)


@app.post("/api/missions/{mission_id}/control")
async def mission_control(
    mission_id: str,
    payload: ControlMessage,
    x_webspider_token: str | None = Header(default=None),
) -> dict[str, Any]:
    if not _authorized(x_webspider_token):
        raise HTTPException(status_code=401, detail="Invalid WebSpider UI token")
    return await run_in_threadpool(registry.get(mission_id).control, payload.action)


@app.get("/api/missions/{mission_id}/events")
async def mission_events(
    mission_id: str,
    after: int = Query(default=0, ge=0),
    x_webspider_token: str | None = Header(default=None),
) -> dict[str, Any]:
    if not _authorized(x_webspider_token):
        raise HTTPException(status_code=401, detail="Invalid WebSpider UI token")
    return {"events": await run_in_threadpool(registry.get(mission_id).events, after)}


@app.websocket("/ws/missions/{mission_id}")
async def mission_websocket(websocket: WebSocket, mission_id: str, token: str | None = Query(default=None)) -> None:
    if not _origin_allowed(websocket.headers.get("origin"), str(websocket.base_url)):
        await websocket.close(code=4403)
        return
    if not _authorized(token or websocket.headers.get("x-webspider-token")):
        await websocket.close(code=4401)
        return
    try:
        supervisor = registry.get(mission_id)
    except HTTPException:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    cursor = 0
    try:
        while True:
            events = await run_in_threadpool(supervisor.events, cursor)
            for event in events:
                cursor = max(cursor, int(event["id"]))
                await websocket.send_json(event)
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
            except TimeoutError:
                continue
            message_type = message.get("type")
            if message_type == "message":
                await run_in_threadpool(supervisor.send_message, str(message.get("text", "")))
            elif message_type == "control":
                await run_in_threadpool(supervisor.control, str(message.get("action", "")))
            elif message_type == "browser":
                await run_in_threadpool(supervisor.browser_command, dict(message.get("action", {})))
    except (WebSocketDisconnect, KeyError):
        return


def configure_runtime(mcp_tools: list | None = None, model: Any = None) -> None:
    """Configure the shared runtime before starting Uvicorn."""
    registry.configure(mcp_tools=mcp_tools, model=model)


_UI_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>WebSpider</title>
<style>body{font:15px system-ui;margin:2rem;max-width:1100px}textarea{width:100%;height:5rem}button{margin:.25rem;padding:.5rem}.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}pre{background:#f4f4f4;padding:1rem;min-height:15rem;overflow:auto}</style></head>
<body><h1>WebSpider</h1><p>Start a mission, then use chat or takeover controls.</p>
<div class="grid"><section><input id="token" type="password" placeholder="UI token (if configured)"><textarea id="mission" placeholder='{"goal":"Map API","start_url":"https://example.com","allowed_domains":["example.com"]}'></textarea><button onclick="start()">Start</button><input id="id" placeholder="mission id"><div><button onclick="control('pause')">Pause</button><button onclick="control('takeover')">Takeover</button><button onclick="control('release')">Release</button><button onclick="control('resume')">Resume</button></div></section><section><pre id="log"></pre></section></div>
<textarea id="chat" placeholder="Instruction for WebSpider"></textarea><button onclick="send()">Send</button>
<script>let ws;const log=x=>document.querySelector('#log').textContent+=JSON.stringify(x,null,2)+'\\n';const auth=()=>{let t=document.querySelector('#token').value;return t?{'X-WebSpider-Token':t}:{} };async function start(){let p=JSON.parse(document.querySelector('#mission').value);let r=await fetch('/api/missions',{method:'POST',headers:{'content-type':'application/json',...auth()},body:JSON.stringify(p)});let d=await r.json();document.querySelector('#id').value=d.mission_id;connect(d.mission_id);log(d)}function connect(id){let t=encodeURIComponent(document.querySelector('#token').value);ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws/missions/'+id+(t?'?token='+t:''));ws.onmessage=e=>log(JSON.parse(e.data))}function send(){ws&&ws.send(JSON.stringify({type:'message',text:document.querySelector('#chat').value}))}function control(a){ws&&ws.send(JSON.stringify({type:'control',action:a}))}</script></body></html>"""
