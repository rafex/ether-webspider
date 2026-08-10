# AGENTS.md

Eres un agente operando en el repositorio `ether-webspider`.

## Que es SpecNative

SpecNative es un modelo de desarrollo donde las especificaciones,
decisiones arquitectonicas y el estado del trabajo viven en el
repositorio. El repositorio es el contexto. No necesitas que te
expliquen el proyecto en el chat.

Cualquier agente — Claude Code, Codex, Cursor, Gemini, o cualquier
otro — puede entrar a este repositorio y continuar exactamente donde
lo dejo el anterior. Sin friccion. Sin perder contexto.

## Donde esta todo

Todo el contexto del proyecto vive en `spec-native/`.
Lee `spec-native/README.md` para el indice completo.

## Si vienes de otro agente

Antes de empezar a trabajar, verifica si hay sesion activa leyendo
`spec-native/SESSION.md`. Si `SESSION.md` tiene `state = "idle"`,
no hay trabajo activo.

## Flujo de trabajo

1. Leer `AGENTS.md` y `spec-native/README.md`.
2. Ejecutar `resume()` mediante el MCP de SpecNative y revisar
   `spec-native/SESSION.md`.
3. Si es una nueva iniciativa, leer `spec-native/ROADMAP.md`,
   `spec-native/PRODUCT.md` y las decisiones relacionadas.
4. Crear o revisar una SPEC en `spec-native/specs/`.
5. Derivar tareas en `spec-native/tasks/` con dependencias, validación y
   criterio de cierre observable.
6. Implementar siguiendo `spec-native/workflows/IMPLEMENTATION.md`.
7. Actualizar tareas mediante el MCP; una tarea `done` requiere
   `completion_evidence`.
8. Registrar decisiones persistentes en `spec-native/DECISIONS.md` o en
   `spec-native/decisions/`.
9. Ejecutar `checkpoint()` antes de pausar o cambiar de agente.
10. Al cerrar una iniciativa, revisar criterios, actualizar
    `spec-native/TRACEABILITY.md` y dejar `SESSION.md` consistente.

## Herramientas SpecNative

El servidor local está en `.specnative/specnative_mcp.py` y usa el entorno
`.specnative/.venv/`. Los agentes deben usar sus resources y tools para
`resume`, `status`, `validate`, `board`, `read_spec`, `update_task`,
`checkpoint` y registro de decisiones. Los comandos comunes se generan desde
`.specnative/commands.json` para Claude Code, OpenCode y Codex.

## Separacion semantica de documentos

- `spec-native/specs/*/SPEC.md` — *que* debe construirse
- `spec-native/DECISIONS.md` — *por que* el sistema es como es
- `spec-native/PRODUCT.md` — *para quien y por que* existe
- `spec-native/ROADMAP.md` — *que viene primero*
- `spec-native/ARCHITECTURE.md` — *como esta estructurado*
- `spec-native/SESSION.md` — *donde esta el trabajo* ahora mismo

## Estados obligatorios

- Toda spec debe declarar: `draft | active | blocked | done | superseded`
- Toda tarea debe declarar: `todo | in_progress | blocked | done`
- Toda decision debe declarar: `proposed | accepted | deprecated | replaced`
- `SESSION.md` debe declarar: `idle | in_progress | blocked | waiting_handoff`
