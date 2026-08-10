# IMPLEMENTATION.md

Procedimiento operativo para implementar tareas.

## Orden de ejecucion

1. Leer `AGENTS.md`, `SESSION.md`, la spec y el task file de la iniciativa.
2. Ejecutar `resume()` y comprobar que no existe trabajo incompatible activo.
3. Leer decisiones, arquitectura y convenciones relevantes.
4. Seleccionar una tarea `todo` cuyas dependencias estén `done`.
5. Cambiarla a `in_progress` y guardar un checkpoint con la intención.
6. Implementar el cambio y escribir tests junto con el código.
7. Ejecutar la validación declarada en la tarea.
8. Cambiar a `done` solo con `completion_evidence` real; si no puede
   continuar, registrar `blocked` y la dependencia.
9. Registrar decisiones persistentes mediante el MCP.
10. Actualizar trazabilidad y guardar checkpoint antes de pausar.

## Antes de cada tarea

- Verificar que las dependencias están instaladas (`uv pip install -e ".[dev]"`).
- Leer el contexto minimo necesario: spec section relevante + archivos
  existentes que seran modificados.

## Durante cada tarea

- Seguir las convenciones en `CONVENTIONS.md`.
- Escribir tests unitarios junto con el codigo.
- No hacer requests reales en tests unitarios (mock MCP, mock LLM).
- Mantener la cobertura >=80% cuando la spec lo exija.

## Despues de cada tarea

- `ruff check <archivos>` — debe pasar limpio cuando ruff esté configurado.
- `mypy <archivos>` — debe pasar limpio cuando mypy esté configurado.
- `pytest tests/ -v --cov` — los tests nuevos pasan.
- Revisar `git diff --check` y el estado de los artefactos SpecNative.

## Al finalizar la iniciativa

- Verificar todos los criterios de aceptación en SPEC.md.
- Actualizar `TRACEABILITY.md`.
- Marcar la spec como `done` solo si no queda trabajo requerido.
- Actualizar `SESSION.md` a `idle` únicamente al cerrar la iniciativa.
