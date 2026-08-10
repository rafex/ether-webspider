# SPEC.md — Auditoría y evolución de ether-rules

```toml
artifact_type = "spec"
id            = "SPEC-ETHER-RULES-0001"
state         = "active"
owner         = "team"
created_at    = "2026-08-09"
updated_at    = "2026-08-09"
replaces      = "none"
related_tasks = ["TASK-ETHER-RULES-0001", "TASK-ETHER-RULES-0002", "TASK-ETHER-RULES-0003", "TASK-ETHER-RULES-0004", "TASK-ETHER-RULES-0005", "TASK-ETHER-RULES-0006"]
related_decisions = ["DEC-0007"]
artifacts     = ["/Users/rafex/repository/github/rafex/ether/ether-my-best-practice"]
validation    = ["make check en ether-my-best-practice", "mkdocs build --strict", "smoke test del MCP ether-rules", "revisión contra rules/01..16"]
```

## Resumen

Auditar y evolucionar el repositorio `ether-my-best-practice` para que sus
reglas sean verificables, su MCP sea instalable y sus plantillas no prometan
automatizaciones que el repositorio no puede ejecutar.

## Problema

`ether-rules` contiene reglas, templates, documentación y un MCP, pero varios
controles son declarativos o están incompletos: no hay una suite de tests del
MCP, MkDocs strict falla, los hooks no están activos por defecto, Commitizen
referencia archivos inexistentes y la documentación no siempre coincide con
la estructura empaquetada.

WebSpider es el consumidor principal de estas reglas y necesita una fuente de
verdad trazable para abordar las correcciones por fases sin mezclar el
estándar mantenedor con las plantillas de proyectos consumidores.

## Objetivo

Dejar una matriz verificable de cumplimiento y abordar progresivamente los
gaps de `ether-my-best-practice`, priorizando documentación, calidad, MCP,
seguridad y CI/CD.

## Alcance

Incluye:

- reglas `01` a `16` de `ether-my-best-practice`;
- Makefile, Justfile, helpers, documentación, MCP, paquete e instalador;
- pruebas, hooks, Commitizen, secretos, CI, CD y templates;
- compatibilidad del MCP con Codex, Claude y OpenCode.

No incluye:

- implementar todas las correcciones en esta iniciativa inicial;
- cambiar el objetivo funcional de WebSpider;
- convertir `ether-my-best-practice` en un servicio desplegable;
- tratar reglas no aplicables al repositorio mantenedor como fallos del
  proyecto sin documentar la excepción.

## Matriz inicial de cumplimiento

| Regla | Estado | Evidencia o gap |
| --- | --- | --- |
| 01 Build tooling | parcial alto | Makefile, Justfile y helpers existen; falta robustez de gates completos. |
| 02 Arquitectura | no aplicable directo | Se orienta principalmente a proyectos consumidores y templates. |
| 03 Testing | no cumple | No existe suite propia del repositorio mantenedor. |
| 04 Documentación | parcial | MkDocs existe, pero strict falla por configuración y hay enlaces obsoletos. |
| 05 Version control | parcial | Historial convencional; hooks y protección de `main` no están garantizados localmente. |
| 06 CI | parcial | Hay workflow de Pages, pero faltan tests completos y CI local reproducible. |
| 07 Agents/MCP | parcial alto | Resources, tools y prompts existen; hay divergencias de rutas y empaquetado. |
| 08 Stack | parcial | Python/uv/MkDocs están presentes; falta Containerfile y fijación adecuada del MCP. |
| 09 Repository structure | cumple con excepción | El mantenedor tiene estructura propia y los consumidores usan templates. |
| 10 Git hooks | parcial | Hooks existen, pero `core.hooksPath` no está activo y falta un target `test`. |
| 11 Commitizen | parcial | Configuración existente con referencias a archivos inexistentes. |
| 12 Gitignore | cumple | Artefactos, caches, entornos y secretos planos están excluidos. |
| 13 Secretos | parcial | sops+age está documentado, pero el recipient es placeholder y faltan scanners. |
| 14 Config files | parcial alto | `.config` centraliza la mayoría; aún hay referencias y configuraciones inconsistentes. |
| 15 Script reuse | cumple mayormente | Librerías compartidas y helpers existen; el paquete MCP debe probar sincronización. |
| 16 CD | no aplicable/parcial | Es una herramienta local; falta definir con precisión el release portable. |

## Requisitos funcionales

- RF-1: La auditoría debe conservar evidencia de cada regla y su estado.
- RF-2: Cada fase debe tener tareas con dependencias y criterio de cierre.
- RF-3: El MCP de ether-rules debe probarse como paquete instalado y desde
  fuente.
- RF-4: Los cambios deben distinguir el repositorio mantenedor de los
  proyectos generados.
- RF-5: Los agentes deben poder consultar y actualizar esta iniciativa usando
  el flujo SpecNative.

## Requisitos no funcionales

- RNF-1: No sobrescribir cambios no comprometidos del repositorio mantenedor.
- RNF-2: No persistir secretos en SPEC, TASKS, checkpoints o reportes.
- RNF-3: Toda tarea cerrada debe registrar evidencia observable.
- RNF-4: Los adaptadores de agentes deben derivarse de
  `.specnative/commands.json`.

## Criterios de aceptación

- Dado el repositorio `ether-my-best-practice`, cuando se consulta la SPEC,
  entonces se puede conocer el estado de las 16 reglas y su evidencia.
- Dada una fase pendiente, cuando se consulta `board()`, entonces sus tareas
  aparecen como `ready`, `waiting`, `in_progress`, `blocked` o `done` según
  metadata y dependencias.
- Dado un task file, cuando una tarea pasa a `done`, entonces contiene
  `completion_evidence` no vacío.
- Dado el MCP local, cuando se ejecuta con `--repo` apuntando a WebSpider,
  entonces expone `validate`, `status`, `board`, `resume`, `update_task` y
  las herramientas de contexto.
- Dado Codex, Claude Code y OpenCode, cuando cargan el repositorio, entonces
  comparten los comandos definidos en `.specnative/commands.json`.

## Dependencias y riesgos

- El MCP requiere Python compatible y la dependencia `mcp` instalada en
  `.specnative/.venv/`.
- El repositorio `ether-my-best-practice` puede tener cambios no
  comprometidos; la reconciliación debe ser incremental.
- Algunas reglas son para proyectos consumidores y no pueden evaluarse como
  defectos del repositorio mantenedor sin una excepción documentada.
- Los cambios de seguridad y hooks pueden afectar el flujo local de commits.

## Plan de validación

1. Ejecutar `health_check()`, `status()`, `validate()` y `board()` en WebSpider.
2. Ejecutar `make check` y `mkdocs build --strict` en ether-rules.
3. Probar importación, handshake, resources, tools y prompts del MCP.
4. Validar JSON de OpenCode y TOML de Codex.
5. Revisar `git diff --check`, trazabilidad y ausencia de secretos.
