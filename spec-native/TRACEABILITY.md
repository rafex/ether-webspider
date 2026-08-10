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

## Iniciativa: ether-rules-compliance

| Artefacto | Ubicacion | Vinculado a |
|-----------|-----------|-------------|
| SPEC | `specs/ether-rules-compliance/SPEC.md` | — |
| TASKS | `tasks/ether-rules-compliance/TASKS.md` | SPEC |
| DEC-0007 | `DECISIONS.md` | SPEC, TASKS |
| ether-rules repository | `/Users/rafex/repository/github/rafex/ether/ether-my-best-practice` | TASKS 0001–0006 |
| Regla 01–16 | `ether-my-best-practice/rules/` | SPEC |

## Cross-repo

| Vinculo | Repo destino | Artefacto |
|---------|-------------|-----------|
| ether-websearch MCP server | ether-websearch | `websearch/src/mcp/mcp_server.py` |
| Feature requests | ether-websearch | `spec-native/intake/IDEAS.md` |
| MCP REST dependency | ether-websearch | DEC-0015, DEC-0016 (ether-websearch) |
| ether-rules standard | ether-my-best-practice | `rules/01-build-tooling.md` … `rules/16-cd.md` |
