# TASKS.md — Auditoría y evolución de ether-rules

```toml
artifact_type = "task_file"
initiative    = "ether-rules-compliance"
spec_id       = "SPEC-ETHER-RULES-0001"
owner         = "team"
state         = "todo"
```

## Fase 1 — Documentación y configuración

### TASK-ETHER-RULES-0001 - Corregir documentación y configuración de ether-rules

```toml
id = "TASK-ETHER-RULES-0001"
title = "Corregir documentación y configuración de ether-rules"
state = "todo"
priority = "p1"
owner = "team"
dependencies = []
expected_files = ["README.md", "docs/**", "mcp/**", ".config/**"]
close_criteria = "MkDocs strict, links principales y configuración de Commitizen/MCP son coherentes con la estructura real."
validation = ["make validate", "mkdocs build --strict", "revisión de enlaces y rutas"]
completion_evidence = []
```

Corregir referencias obsoletas, `site_email`, rutas del paquete, archivos de
versión inexistentes y cualquier promesa de capacidades no implementadas.

## Fase 2 — Tests del compilador y MCP

### TASK-ETHER-RULES-0002 - Crear suite de tests para reglas y MCP

```toml
id = "TASK-ETHER-RULES-0002"
title = "Crear suite de tests para reglas y MCP"
state = "todo"
priority = "p0"
owner = "team"
dependencies = ["TASK-ETHER-RULES-0001"]
expected_files = ["tests/**", "helpers/python/**", "mcp/**"]
close_criteria = "Compilador, resources, tools, prompts, scaffolding y check_project tienen tests reproducibles."
validation = ["pytest tests/ -v", "cobertura del MCP y compilador", "sin red en tests unitarios"]
completion_evidence = []
```

## Fase 3 — Empaquetado e instalación

### TASK-ETHER-RULES-0003 - Validar wheel, instalación y smoke test MCP

```toml
id = "TASK-ETHER-RULES-0003"
title = "Validar wheel, instalación y smoke test MCP"
state = "todo"
priority = "p0"
owner = "team"
dependencies = ["TASK-ETHER-RULES-0002"]
expected_files = ["mcp/pyproject.toml", "helpers/shell/mcp-install.sh", ".github/workflows/release.yml"]
close_criteria = "El wheel instala en entorno limpio, verifica checksum y expone resources, tools y prompts."
validation = ["uv build", "instalación en venv limpio", "handshake MCP", "checksum SHA-256"]
completion_evidence = []
```

## Fase 4 — Hooks, Commitizen y secretos

### TASK-ETHER-RULES-0004 - Hacer efectivos los gates locales y secretos

```toml
id = "TASK-ETHER-RULES-0004"
title = "Hacer efectivos los gates locales y secretos"
state = "todo"
priority = "p1"
owner = "team"
dependencies = ["TASK-ETHER-RULES-0002"]
expected_files = [".githooks/**", "helpers/shell/**", ".config/commitizen/**", ".config/sops/**", ".gitignore"]
close_criteria = "Hooks, Commitizen y sops+age funcionan o fallan explícitamente cuando falta una dependencia obligatoria."
validation = ["hooks install", "commit-msg válido e inválido", "gitleaks/trufflehog", "sops/age dry run"]
completion_evidence = []
```

## Fase 5 — CI/CD y stack

### TASK-ETHER-RULES-0005 - Completar CI local, Containerfile y CD documentado

```toml
id = "TASK-ETHER-RULES-0005"
title = "Completar CI local, Containerfile y CD documentado"
state = "todo"
priority = "p2"
owner = "team"
dependencies = ["TASK-ETHER-RULES-0003", "TASK-ETHER-RULES-0004"]
expected_files = ["Containerfile.ci", "helpers/mk/**", "helpers/shell/**", ".github/workflows/**", "docs/**"]
close_criteria = "Los gates locales y CI ejecutan validación, tests, empaquetado y publicación con responsabilidades claras."
validation = ["make ci", "build de Containerfile", "workflow YAML", "revisión de CD.md"]
completion_evidence = []
```

## Fase 6 — Revisión y cierre

### TASK-ETHER-RULES-0006 - Revisar matriz, trazabilidad y cierre por fases

```toml
id = "TASK-ETHER-RULES-0006"
title = "Revisar matriz, trazabilidad y cierre por fases"
state = "todo"
priority = "p1"
owner = "team"
dependencies = ["TASK-ETHER-RULES-0001", "TASK-ETHER-RULES-0002", "TASK-ETHER-RULES-0003", "TASK-ETHER-RULES-0004", "TASK-ETHER-RULES-0005"]
expected_files = ["spec-native/specs/ether-rules-compliance/SPEC.md", "spec-native/tasks/ether-rules-compliance/TASKS.md", "spec-native/TRACEABILITY.md"]
close_criteria = "Cada criterio de aceptación tiene evidencia; la matriz distingue cumplido, parcial, no aplicable y pendiente."
validation = ["health_check()", "status()", "validate()", "board()", "review_against_spec"]
completion_evidence = []
```
