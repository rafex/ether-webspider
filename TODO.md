# TODO.md — Tablero de tareas

## Active

_(ninguna — todas las tareas completadas)_

## Done

- [x] T-001: Bootstrap SpecNative completo
- [x] T-002: Scaffold Python (pyproject, package, config LLM)
- [x] T-003: Conector MCP (MCPClient + orquestacion REST)
- [x] T-004: Capabilities inventory + tool request_capability
- [x] T-005: Checkpoint engine v2 (state tools + memory persist + resume, bugs A1-A3)
- [x] T-006: Motor de mision (parser, prompt, reporte)
- [x] T-007: CLI run/resume + documentacion
- [x] T-008: Tests + gates (36 pass + MCP smoke real verificado)
- [x] T-009: Traceability + registro decisiones (DEC-0001..0004)

## Fixes (A1-E completados)

- [x] A1: Fix step_callback signature (memory_step, agent)
- [x] A2: Fix save_memory — step.dict() + json default=str
- [x] A3: Fix resume_mission — AgentMemory(system_prompt=...) + best-effort restore
- [x] A4: pyproject.toml → smolagents[mcp] (mcpadapt install)
- [x] B: State tools: add_finding, mark_visited, add_to_frontier, state_summary
- [x] C: Fix prompt (remove variable state, instruct state tools)
- [x] D: test_agent.py con FakeModel + test checkpoint con ActionStep real
- [x] E: Smoke MCP real: 15 tools loaded via ether-websearch REST+MCP
- [x] F: SESSION/SPEC/TODO updated, gates verified

## Pending

_(ninguna)_
