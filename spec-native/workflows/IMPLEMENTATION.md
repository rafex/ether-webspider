# IMPLEMENTATION.md

Procedimiento operativo para implementar tareas.

## Orden de ejecucion

1. Leer la spec (`specs/<iniciativa>/SPEC.md`) y las tareas
   (`tasks/<iniciativa>/TASKS.md`).
2. Leer decisiones relevantes en `DECISIONS.md`.
3. Ejecutar tareas en orden T-001 → T-009.
4. Cada tarea produce archivos especificos documentados en `TASKS.md`.
5. Al completar una tarea, marcarla `[x]` en `TODO.md` y actualizar
   `TASKS.md`.
6. Si una decision emerge durante la implementacion, registrarla en
   `DECISIONS.md`.

## Antes de cada tarea

- Verificar que las dependencias estan instaladas (`uv pip install -e ".[dev]"`).
- Leer el contexto minimo necesario: spec section relevante + archivos
  existentes que seran modificados.

## Durante cada tarea

- Seguir las convenciones en `CONVENTIONS.md`.
- Escribir tests unitarios junto con el codigo.
- No hacer requests reales en tests unitarios (mock MCP, mock LLM).
- Mantener la cobertura >=80%.

## Despues de cada tarea

- `ruff check <archivos>` — debe pasar limpio.
- `mypy <archivos>` — debe pasar limpio.
- `pytest tests/ -v --cov` — los tests nuevos pasan.
- Commit con mensaje Conventional Commit.

## Al finalizar la iniciativa

- Verificar todos los criterios de aceptacion en SPEC.md.
- Actualizar `TRACEABILITY.md`.
- Marcar spec como `done`.
- Actualizar `SESSION.md` a `idle`.
- Marcar todos los items en `TODO.md` como `[x]`.
