# TASKS.md — Iniciativa webspider-agent

Tareas ejecutables derivadas de `specs/webspider-agent/SPEC.md`.

---

## T-001 — Bootstrap SpecNative

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

## T-002 — Scaffold Python

- **Estado:** done
- **Archivos esperados:**
  - `pyproject.toml` con dependencias (smolagents, mcp, ether-websearch)
  - `webspider/__init__.py`
  - `webspider/config.py` — factory LLM multi-proveedor
  - `.gitignore` actualizado con venv, checkpoints/, etc.
- **Validacion:** `uv pip install -e ".[dev]"` funciona, `from webspider.config import get_model` no falla.

---

## T-003 — Conector MCP

- **Estado:** done
- **Archivos esperados:**
  - `webspider/mcp_client.py` — `get_mcp_tools()` via MCPClient
  - `Justfile` con task `up` que levanta REST + MCP de ether-websearch
- **Validacion:** `get_mcp_tools()` retorna lista de tools (requiere
  ether-websearch instalado y REST corriendo).

---

## T-004 — Capabilities + request_capability

- **Estado:** done
- **Archivos esperados:**
  - `webspider/capabilities.py` — `get_capabilities_tools()`
  - Bridge que escribe feature requests en
    `<ETHER_WEBSEARCH_REPO>/spec-native/intake/IDEAS.md`
- **Validacion:** ejecutar `request_capability(...)` y verificar que
  el archivo IDEAS.md recibe la entrada.

---

## T-005 — Checkpoint engine

- **Estado:** done
- **Archivos esperados:**
  - `webspider/checkpoint.py` — `save_checkpoint`, `load_checkpoint`,
    tool wrappers para el agente, step callback.
- **Validacion:** test unitario round-trip: save → load → mismo estado.

---

## T-006 — Motor de mision

- **Estado:** done
- **Archivos esperados:**
  - `webspider/mission.py` — parser CLI/JSON, prompt builder, reporte.
- **Validacion:** `mission_from_args(...)` produce dict valido contra
  schema esperado.

---

## T-007 — Agente + CLI

- **Estado:** done
- **Archivos esperados:**
  - `webspider/agent.py` — `run_mission`, `resume_mission`
  - `webspider/cli.py` — entry point con argparse
- **Validacion:** `python -m webspider.cli run --help` muestra ayuda.

---

## T-008 — Tests + gates CI

- **Estado:** done
- **Archivos esperados:**
  - `tests/test_config.py`
  - `tests/test_checkpoint.py`
  - `tests/test_mission.py`
  - `tests/test_capabilities.py`
  - `.github/workflows/ci.yml`
- **Validacion:** `pytest tests/ -v --cov=webspider` pasa con >=80%.

---

## T-009 — Traceability + DECs

- **Estado:** done
- **Archivos esperados:**
  - `spec-native/DECISIONS.md` con DEC-0001..0004
  - `spec-native/TRACEABILITY.md` actualizado
  - `spec-native/SESSION.md` actualizado a idle
  - `TODO.md` con todos los items marcados done
- **Validacion:** todos los archivos existen y DECs tienen estados
  validos.
