# TASKS.md — Iniciativa webspider-agent

```toml
artifact_type = "task_file"
initiative = "webspider-agent"
spec_id = "SPEC-WEBSPIDER-0001"
owner = "team"
state = "done"
```

Tareas ejecutables derivadas de `specs/webspider-agent/SPEC.md`.

---

### TASK-WEBSPIDER-0001 - Bootstrap SpecNative

```toml
id = "TASK-WEBSPIDER-0001"
title = "Bootstrap SpecNative"
state = "done"
priority = "p0"
owner = "team"
dependencies = []
expected_files = ["AGENTS.md", "spec-native/**", ".specnative/**"]
close_criteria = "El contexto SpecNative y sus documentos base existen y son navegables."
validation = ["health_check()", "validate()", "revisión de documentos"]
completion_evidence = ["SpecNative MCP health_check() reportó 8/8 documentos saludables."]
```

- **Estado:** done
- **Archivos esperados:**
  - `AGENTS.md`, `README.md`, `TODO.md`
  - `spec-native/`: README, PRODUCT, ARCHITECTURE, STACK, CONVENTIONS,
    COMMANDS, DECISIONS, ROADMAP, TRACEABILITY, SESSION
  - `spec-native/specs/webspider-agent/SPEC.md`
  - `spec-native/tasks/webspider-agent/TASKS.md` (este archivo)
  - `spec-native/workflows/IMPLEMENTATION.md`
  - `spec-native/pipelines/CI.md`
- **Validacion:** `specnative validate` (si esta disponible) o revision
  manual de que todos los documentos existen y siguen el formato.

---

### TASK-WEBSPIDER-0002 - Scaffold Python

```toml
id = "TASK-WEBSPIDER-0002"
title = "Scaffold Python"
state = "done"
priority = "p0"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0001"]
expected_files = ["pyproject.toml", "webspider/**"]
close_criteria = "El paquete Python y la factory LLM están disponibles con dependencias declaradas."
validation = ["uv pip install -e \".[dev]\"", "import webspider.config"]
completion_evidence = ["El paquete y la configuración LLM están presentes en pyproject.toml y webspider/config.py."]
```

- **Estado:** done
- **Archivos esperados:**
  - `pyproject.toml` con dependencias (smolagents, mcp, ether-websearch)
  - `webspider/__init__.py`
  - `webspider/config.py` — factory LLM multi-proveedor
  - `.gitignore` actualizado con venv, checkpoints/, etc.
- **Validacion:** `uv pip install -e ".[dev]"` funciona, `from webspider.config import get_model` no falla.

---

### TASK-WEBSPIDER-0003 - Conector MCP

```toml
id = "TASK-WEBSPIDER-0003"
title = "Conector MCP"
state = "done"
priority = "p0"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0002"]
expected_files = ["webspider/mcp_client.py", "Justfile"]
close_criteria = "El agente puede cargar las tools de ether-websearch mediante MCP."
validation = ["mcp client smoke test", "just up"]
completion_evidence = ["MCP client y task de arranque están implementados; la integración remota se valida en el entorno ether-websearch."]
```

- **Estado:** done
- **Archivos esperados:**
  - `webspider/mcp_client.py` — `get_mcp_tools()` via MCPClient
  - `Justfile` con task `up` que levanta REST + MCP de ether-websearch
- **Validacion:** `get_mcp_tools()` retorna lista de tools (requiere
  ether-websearch instalado y REST corriendo).

---

### TASK-WEBSPIDER-0004 - Capabilities y request_capability

```toml
id = "TASK-WEBSPIDER-0004"
title = "Capabilities y request_capability"
state = "done"
priority = "p1"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0003"]
expected_files = ["webspider/capabilities.py", "spec-native/intake/IDEAS.md"]
close_criteria = "Los gaps de capacidad se convierten en solicitudes trazables para ether-websearch."
validation = ["pytest tests/test_capabilities.py"]
completion_evidence = ["La bridge request_capability escribe feature requests en el intake de ether-websearch."]
```

- **Estado:** done
- **Archivos esperados:**
  - `webspider/capabilities.py` — `get_capabilities_tools()`
  - Bridge que escribe feature requests en
    `<ETHER_WEBSEARCH_REPO>/spec-native/intake/IDEAS.md`
- **Validacion:** ejecutar `request_capability(...)` y verificar que
  el archivo IDEAS.md recibe la entrada.

---

### TASK-WEBSPIDER-0005 - Checkpoint engine

```toml
id = "TASK-WEBSPIDER-0005"
title = "Checkpoint engine"
state = "done"
priority = "p0"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0003"]
expected_files = ["webspider/checkpoint.py", "tests/test_checkpoint.py"]
close_criteria = "State y memoria se guardan y restauran sin perder el progreso de misión."
validation = ["pytest tests/test_checkpoint.py"]
completion_evidence = ["La suite reportó round-trip de checkpoints y persistencia de memoria."]
```

- **Estado:** done
- **Archivos esperados:**
  - `webspider/checkpoint.py` — `save_checkpoint`, `load_checkpoint`,
    tool wrappers para el agente, step callback.
- **Validacion:** test unitario round-trip: save → load → mismo estado.

---

### TASK-WEBSPIDER-0006 - Motor de misión

```toml
id = "TASK-WEBSPIDER-0006"
title = "Motor de misión"
state = "done"
priority = "p0"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0005"]
expected_files = ["webspider/mission.py", "tests/test_mission.py"]
close_criteria = "Las misiones se parsean, generan prompt y producen reporte."
validation = ["pytest tests/test_mission.py"]
completion_evidence = ["La suite de misión pasa y el parser CLI/JSON está implementado."]
```

- **Estado:** done
- **Archivos esperados:**
  - `webspider/mission.py` — parser CLI/JSON, prompt builder, reporte.
- **Validacion:** `mission_from_args(...)` produce dict valido contra
  schema esperado.

---

### TASK-WEBSPIDER-0007 - Agente y CLI

```toml
id = "TASK-WEBSPIDER-0007"
title = "Agente y CLI"
state = "done"
priority = "p0"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0006"]
expected_files = ["webspider/agent.py", "webspider/cli.py"]
close_criteria = "run, resume y list-checkpoints están disponibles desde la CLI."
validation = ["python -m webspider.cli run --help", "pytest tests/ -v"]
completion_evidence = ["La CLI y el agente están implementados y cubiertos por la suite disponible."]
```

- **Estado:** done
- **Archivos esperados:**
  - `webspider/agent.py` — `run_mission`, `resume_mission`
  - `webspider/cli.py` — entry point con argparse
- **Validacion:** `python -m webspider.cli run --help` muestra ayuda.

---

### TASK-WEBSPIDER-0008 - Tests y gates CI

```toml
id = "TASK-WEBSPIDER-0008"
title = "Tests y gates CI"
state = "done"
priority = "p0"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0007"]
expected_files = ["tests/**", ".github/workflows/ci.yml"]
close_criteria = "Los tests y gates declarados por WebSpider pasan con cobertura objetivo."
validation = ["pytest tests/ -v --cov=webspider", "ruff check", "mypy"]
completion_evidence = ["SESSION.md registra 49 tests de WebSpider y gates ruff/mypy limpios."]
```

- **Estado:** done
- **Archivos esperados:**
  - `tests/test_config.py`
  - `tests/test_checkpoint.py`
  - `tests/test_mission.py`
  - `tests/test_capabilities.py`
  - `.github/workflows/ci.yml`
- **Validacion:** `pytest tests/ -v --cov=webspider` pasa con >=80%.

---

### TASK-WEBSPIDER-0009 - Traceability y decisiones

```toml
id = "TASK-WEBSPIDER-0009"
title = "Traceability y decisiones"
state = "done"
priority = "p1"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0008"]
expected_files = ["spec-native/DECISIONS.md", "spec-native/TRACEABILITY.md", "spec-native/SESSION.md"]
close_criteria = "Las decisiones y relaciones principales de la iniciativa están registradas."
validation = ["revisión de DECISIONS.md", "revisión de TRACEABILITY.md", "health_check()"]
completion_evidence = ["DEC-0001 a DEC-0006 y la trazabilidad de webspider-agent están registrados."]
```

- **Estado:** done
- **Archivos esperados:**
  - `spec-native/DECISIONS.md` con DEC-0001..0004
  - `spec-native/TRACEABILITY.md` actualizado
  - `spec-native/SESSION.md` actualizado a idle
  - `TODO.md` con todos los items marcados done
- **Validacion:** todos los archivos existen y DECs tienen estados
  validos.

### TASK-WEBSPIDER-0010 - Sesiones de navegador y control de misión

```toml
id = "TASK-WEBSPIDER-0010"
title = "Sesiones de navegador y control de misión"
state = "done"
priority = "p0"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0009"]
expected_files = ["webspider/supervisor.py", "webspider/server.py", "webspider/secrets.py"]
close_criteria = "Sesiones persistentes, takeover, pause/resume y redacción de secretos funcionan."
validation = ["pytest tests/test_supervisor.py tests/test_secrets.py", "MCP smoke"]
completion_evidence = ["SESSION.md registra supervisor, UI, REPL, takeover y redacción de secretos verificados."]
```

- **Estado:** done
- **Archivos esperados:** `webspider/supervisor.py`, `webspider/server.py`,
  `webspider/secrets.py` y `ether-websearch/websearch/src/browser_sessions.py`.
- **Validacion:** sesiones persistentes, navegador visible, takeover,
  pause/resume, WebSocket y REPL sobre el mismo supervisor; secretos
  ausentes de persistencia.

### TASK-WEBSPIDER-0011 - Drivers y compatibilidad MCP

```toml
id = "TASK-WEBSPIDER-0011"
title = "Drivers y compatibilidad MCP"
state = "done"
priority = "p0"
owner = "team"
dependencies = ["TASK-WEBSPIDER-0010"]
expected_files = ["webspider/tool_adapter.py", "webspider/mcp_client.py"]
close_criteria = "Los drivers y las tools MCP del navegador son compatibles con la misión."
validation = ["pytest tests/ -v", "MCP smoke", "ether-websearch unit suite"]
completion_evidence = ["SESSION.md registra 26 tools MCP cargadas y la suite de ether-websearch verificada."]
```

- **Estado:** done
- **Archivos esperados:** routes y tools MCP `browser_session_*`, Playwright,
  Selenium Chrome/Firefox/Safari y CDP attach.
- **Validacion:** 26 tools MCP, REST/browser-session tests y suite unitaria
  completa de ether-websearch.
