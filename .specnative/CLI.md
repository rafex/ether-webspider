# CLI.md

Referencia del CLI de SpecNative. El uso del CLI es opcional; el contrato
base también puede validarse mediante el MCP local.

## Ubicación

El CLI canónico vive en el repositorio
[SpecNative Development](https://github.com/rafex/SpecNative-Development),
archivo `tools/specnative.py`. Este repositorio conserva la documentación y
el servidor MCP necesarios para trabajar sin instalar el CLI global.

## Comandos

```bash
python3 /path/to/SpecNative-Development/tools/specnative.py \
  status --target /path/to/ether-webspider

python3 /path/to/SpecNative-Development/tools/specnative.py \
  validate --target /path/to/ether-webspider

python3 /path/to/SpecNative-Development/tools/specnative.py \
  board --target /path/to/ether-webspider

python3 /path/to/SpecNative-Development/tools/specnative.py \
  export-index --target /path/to/ether-webspider \
  --output /tmp/webspider-spec-index.json
```

Las salidas `board` y `export-*` son derivadas. Nunca se edita el tablero
para cambiar estados: la fuente de verdad es `TASKS.md`.

## Validación mediante MCP

El MCP local expone las mismas operaciones principales:

- `resume()` y `status()` para continuidad y estado;
- `validate()` para documentos y metadata;
- `board()` para la vista derivada;
- `read_spec()` y `list_tasks()` para contexto;
- `update_task()` para estados y evidencia;
- `checkpoint()` para handoff multi-agente.

Ejecutar el servidor localmente:

```bash
.specnative/.venv/bin/python3 .specnative/specnative_mcp.py \
  --repo "$(pwd)"
```

## Metadata TOML

Las specs deben declarar `artifact_type`, `id`, `state`, `owner`,
`created_at` y `updated_at`. Los task files deben declarar `artifact_type`,
`initiative`, `spec_id`, `owner` y `state`; cada tarea debe incluir
`id`, `title`, `state`, `owner`, `dependencies`, `close_criteria` y
`validation`. Una tarea `done` debe tener `completion_evidence` no vacío.
