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

1. Si hay sesion activa: leer `spec-native/SESSION.md`.
2. Si es una nueva iniciativa: leer `spec-native/ROADMAP.md` y
   `spec-native/PRODUCT.md` para entender contexto.
3. Implementar siguiendo `spec-native/workflows/IMPLEMENTATION.md`.
4. Actualizar tareas y estado en `spec-native/tasks/`.
5. Registrar decisiones en `spec-native/DECISIONS.md`.
6. Al pausar: actualizar `spec-native/SESSION.md`.

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
