# SPEC.md — Iniciativa webspider-agent

```toml
artifact_type = "spec"
id = "SPEC-WEBSPIDER-0001"
state = "done"
owner = "team"
created_at = "2026-08-07"
updated_at = "2026-08-09"
replaces = "none"
related_tasks = ["TASK-WEBSPIDER-0001", "TASK-WEBSPIDER-0002", "TASK-WEBSPIDER-0003", "TASK-WEBSPIDER-0004", "TASK-WEBSPIDER-0005", "TASK-WEBSPIDER-0006", "TASK-WEBSPIDER-0007", "TASK-WEBSPIDER-0008", "TASK-WEBSPIDER-0009", "TASK-WEBSPIDER-0010", "TASK-WEBSPIDER-0011"]
related_decisions = ["DEC-0001", "DEC-0002", "DEC-0003", "DEC-0004", "DEC-0005", "DEC-0006"]
artifacts = ["webspider/**", "tests/**", "spec-native/**"]
validation = ["pytest tests/ -v", "ruff check webspider/ tests/", "mypy webspider/"]
```

- **Estado:** done
- **Owner:** team
- **Inicio:** 2026-08-07

## Problema

Los agentes de IA necesitan rastrear sitios web de forma inteligente
orientada a un objetivo concreto, con capacidad de checkpoint/resume
para misiones largas. Las herramientas de crawling existentes
(`ether-websearch.spider`) hacen BFS ciego; no hay un agente que
decida *que* explorar basado en un objetivo semantico.

## Objetivo

Construir `ether-webspider`: un agente `CodeAgent` (smolagents) que:

1. Consume las tools de `ether-websearch` via MCP (15 tools).
2. Recibe una mision con objetivo + seed URL(s) y rastrea con
   orientacion al objetivo (el LLM decide que URLs priorizar).
3. Genera checkpoints atomicos (state + memoria) despues de cada
   step, permitiendo `resume`.
4. Detecta gaps de capacidad en ether-websearch y emite feature
   requests al backlog SpecNative de ether-websearch.
5. Soporta multiple backends LLM via configuracion (HF, OpenAI-compatible,
   Ollama local).

## Alcance

### Incluye

- Paquete Python `webspider/` con modulos: config, mcp_client, checkpoint,
  capabilities, mission, agent, cli.
- CLI con comandos `run` y `resume`.
- Checkpoints en `checkpoints/<mission_id>/state.json` +
  `checkpoints/<mission_id>/memory.jsonl`.
- Tool `request_capability` con bridge al backlog SpecNative de
  ether-websearch.
- Tests unitarios (sin red) + 1 test de integracion con sitio de prueba.
- Gates CI: ruff, mypy, pytest.
- Documentacion SpecNative completa + README.
- Justfile con tasks: up, down, test, lint, typecheck, demo.

### No incluye

- Construir nuevas tools en ether-websearch (eso se solicita via backlog).
- API REST o MCP server propio — solo CLI.
- Soporte Windows.
- UI o dashboard.

## Especificacion funcional

### Mision

Una mision se define con:

```json
{
  "goal": "Encontrar el endpoint de login del portal",
  "start_url": "https://www.sat.gob.mx",
  "max_steps": 30,
  "allowed_domains": ["sat.gob.mx"],
  "checkpoint_dir": "checkpoints/"
}
```

El agente recibe un prompt que incluye el objetivo, las tools
disponibles, y la estrategia de exploracion.

### Flujo del agente

1. `fetch_capabilities()` — inventario de tools disponibles.
2. Exploracion inicial: `spider_webpage(start_url, depth=1)` o
   `crawl_webpage(start_url)` — obtiene links, endpoints, contenido.
3. Evaluacion LLM: el modelo analiza resultados contra el objetivo.
   Si encontro → reporte final. Sino → selecciona proximas URLs.
4. Exploracion dirigida: `fetch_webpage(candidate_url)` o
   `spider_webpage(candidate_url)` en URLs priorizadas.
5. Repetir hasta encontrar o `max_steps`.
6. Cada step activa el step callback que guarda checkpoint.

### Checkpoint

```json
// state.json
{
  "mission_id": "sat_20260807",
  "mission": { "goal": "...", "start_url": "...", "max_steps": 30 },
  "step": 12,
  "visited": ["https://...", ...],
  "frontier": [
    {"url": "https://...", "priority": 0.85, "reason": "contiene 'login' en la URL"},
    ...
  ],
  "findings": [
    {"url": "https://.../login.aspx", "type": "login", "confidence": 0.95},
    ...
  ],
  "created_at": "2026-08-07T14:30:00Z",
  "last_step_at": "2026-08-07T14:32:15Z"
}
```

### Resume

```bash
python -m webspider.cli resume --checkpoint checkpoints/sat_20260807
```

1. Carga `state.json` → misión, frontier, findings, step.
2. Carga `memory.jsonl` → steps del agente.
3. Reconstruye `CodeAgent` con `agent.memory.steps = loaded_steps`.
4. Continua con `agent.run(resume_prompt, reset=False)`.
5. El resume_prompt indica al agente el estado actual (step, frontier,
   hallazgos previos).

### Tool gap detection

- El agente recibe `fetch_capabilities()` al inicio (resource MCP).
- Si durante la mision necesita algo no disponible, llama a
  `request_capability(name, description, use_case)`.
- La tool escribe un feature request en
  `<ETHER_WEBSEARCH_REPO>/spec-native/intake/IDEAS.md`.

```json
// Feature request emitido
{
  "capability": "sitemap_xml_fetch",
  "description": "Fetch and parse sitemap.xml to discover all site URLs",
  "use_case": "Durante rastreo de https://example.com, necesito descubrir
              URLs que no estan linkeadas desde la homepage. Un sitemap.xml
              ayudaria a encontrar endpoints ocultos.",
  "requested_by": "ether-webspider",
  "mission_id": "sat_20260807",
  "timestamp": "2026-08-07T14:35:00Z"
}
```

## Criterios de aceptacion

- [ ] `just test` pasa con cobertura >=80%.
- [ ] `just lint` (ruff) y `just typecheck` (mypy) limpios.
- [ ] Demo: agente encuentra endpoint de login en un sitio de prueba
  (ej: books.toscrape.com o mock server local) en <30 pasos.
- [ ] `resume` desde checkpoint continua exactamente donde se detuvo
  (mismo frontier, sin re-explorar URLs visitadas).
- [ ] `request_capability` escribe correctamente en el backlog de
  ether-websearch (verificable abriendo el archivo).
