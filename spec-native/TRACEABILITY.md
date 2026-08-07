# TRACEABILITY.md

Vinculos entre artefactos del proyecto.

## Iniciativa: webspider-agent

| Artefacto | Ubicacion | Vinculado a |
|-----------|-----------|-------------|
| SPEC | `specs/webspider-agent/SPEC.md` | — |
| TASKS | `tasks/webspider-agent/TASKS.md` | SPEC |
| DEC-0001 | `DECISIONS.md` | T-003, SPEC |
| DEC-0002 | `DECISIONS.md` | T-005, SPEC |
| DEC-0003 | `DECISIONS.md` | T-004, SPEC |
| DEC-0004 | `DECISIONS.md` | T-002, SPEC |
| PRODUCT | `PRODUCT.md` | SPEC |
| ARCHITECTURE | `ARCHITECTURE.md` | SPEC |
| STACK | `STACK.md` | T-002 |

## Cross-repo

| Vinculo | Repo destino | Artefacto |
|---------|-------------|-----------|
| ether-websearch MCP server | ether-websearch | `websearch/src/mcp/mcp_server.py` |
| Feature requests | ether-websearch | `spec-native/intake/IDEAS.md` |
| MCP REST dependency | ether-websearch | DEC-0015, DEC-0016 (ether-websearch) |
