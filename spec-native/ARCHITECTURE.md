# ARCHITECTURE.md

Describe la arquitectura de ether-webspider.

## Vision general

**ether-webspider** es un agente LLM que orquesta herramientas de
`ether-websearch` para rastrear sitios web con orientacion al objetivo.
La arquitectura tiene tres capas: configuracion LLM, conector MCP,
y motor de agente con checkpoints.

```
Usuario (CLI)
  │
  ├─ webspider.cli run --goal "..." --start URL
  │     │
  │     ├─ config.get_model() → OpenAIModel | InferenceClientModel | LiteLLMModel
  │     │
  │     ├─ mcp_client.get_tools() → MCPClient (stdio subprocess ether-websearch-mcp)
  │     │     │
  │     │     └─ ether-websearch REST core (uvicorn) ← MCP_REST_BASE_URL
  │     │
  │     ├─ checkpoint.load_or_init(mission_id) → state.json + memory
  │     │
  │     └─ CodeAgent(tools=[...mcp_tools, save_checkpoint, load_checkpoint,
  │                          fetch_capabilities, request_capability],
  │                  model=model)
  │           │
  │           ├─ step 1: spider_webpage(url) → links, endpoints
  │           ├─ step 2: LLM evalua hallazgos vs objetivo
  │           ├─ step 3: fetch_webpage(promising_url) → contenido
  │           ├─ step 4: LLM decide si encontro el objetivo
  │           ├─ [checkpoint tras cada step]
  │           └─ ...
  │
  └─ Resume: webspider.cli resume --checkpoint <id>
        │
        ├─ carga state.json + memory.jsonl
        ├─ reconstruye CodeAgent con memoria previa
        └─ agent.run(mission_prompt, reset=False)
```

## Modulos principales

### `webspider.config`
- **Responsabilidad:** fabrica el modelo LLM segun variables de entorno.
- **Backends:** `openai` (OpenAIModel, compatible con Ollama), `hf`
  (InferenceClientModel), `litellm` (LiteLLMModel).
- **Envs:** `LLM_BACKEND`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE`,
  `LLM_NUM_CTX`.

### `webspider.mcp_client`
- **Responsabilidad:** conecta con el MCP server de ether-websearch
  via `MCPClient` de smolagents, exponiendo las 15 tools como
  herramientas del agente.
- **Orquestacion:** requiere que el REST core de ether-websearch este
  corriendo. Script `just up` levanta ambos procesos.
- **Transporte:** stdio subprocess usando el entry point
  `ether-websearch-mcp`.

### `webspider.checkpoint`
- **Responsabilidad:** persiste y restaura el estado de una mision.
- **State tools:** `save_checkpoint(state)` y `load_checkpoint()` como
  tools del agente para frontier/findings durables.
- **Memoria:** `agent.memory.steps` serializado a `memory.jsonl`.
- **Formato:** `checkpoints/<mission_id>/state.json` +
  `checkpoints/<mission_id>/memory.jsonl`.

### `webspider.capabilities`
- **Responsabilidad:** inventory de capacidades disponibles + tool
  `request_capability(name, description, use_case)`.
- **Bridge:** escribe feature requests al backlog SpecNative de
  ether-websearch (`spec-native/intake/IDEAS.md`) usando la ruta
  configurable `ETHER_WEBSEARCH_REPO`.

### `webspider.mission`
- **Responsabilidad:** parsea la definicion de una mision (CLI args
  o archivo JSON) y genera el prompt del agente + el reporte final.
- **Mision:** `goal`, `start_url`, `max_steps`, `allowed_domains`,
  `backend_llm`.

### `webspider.agent`
- **Responsabilidad:** construye el `CodeAgent` de smolagents con
  todas las herramientas y ejecuta la mision.
- **Step callback:** tras cada step, serializa checkpoint.

### `webspider.cli`
- **Responsabilidad:** CLI principal — `run`, `resume`, `list-checkpoints`.
- **Entry point:** `python -m webspider.cli`.

## Contrato de modulo

Cada modulo privado expone una interfaz publica minima:

```python
# config.py
def get_model() -> Any: ...

# mcp_client.py
def get_mcp_tools() -> list[Any]: ...

# checkpoint.py
def save_checkpoint(mission_id: str, state: dict) -> None: ...
def load_checkpoint(mission_id: str) -> dict: ...

# capabilities.py
def get_capabilities_tools() -> list[Any]: ...

# mission.py
def mission_from_args(goal: str, start: str, ...) -> dict: ...
def build_prompt(mission: dict) -> str: ...

# agent.py
def run_mission(mission: dict) -> dict: ...
def resume_mission(mission_id: str) -> dict: ...
```

## Restricciones de dependencia

| Direccion | Permitido |
|-----------|-----------|
| Modulo → `webspider.config` | ✅ |
| Modulo → `webspider.checkpoint` | ✅ |
| `webspider.agent` → resto de modulos | ✅ |
| Modulo → `websearch.src.*` | ❌ (solo via MCP) |
| Dependencias circulares | ❌ |

## Riesgos

| Riesgo | Impacto | Mitigacion |
|--------|---------|------------|
| MCP requiere REST corriendo | Medio — el agente no arranca | `just up` levanta ambos; documentado |
| Modelo debil no entiende la mision | Alto — rastreo sin sentido | Documentar modelos recomendados por backend |
| Fidelidad del resume | Medio — el LLM puede perder el hilo | State tools garantizan frontier/findings |
| Checkpoints crecen sin limite | Bajo — disco lleno | `max_checkpoints` y `just clean-checkpoints` |
