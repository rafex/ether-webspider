# COMMANDS.md

Comandos del proyecto.

## Desarrollo

```bash
# Crear venv e instalar dependencias
uv venv
uv pip install -e ".[dev]"

# Lint
ruff check webspider/ tests/

# Type check
mypy webspider/

# Tests
pytest tests/ -v

# Tests con cobertura
pytest tests/ -v --cov=webspider --cov-report=term-missing
```

## Ejecucion

```bash
# Levantar REST + MCP de ether-websearch (requiere ether-websearch instalado)
just up

# Detener servicios
just down

# Ejecutar mision
python -m webspider.cli run \
  --goal "Encontrar el endpoint de login" \
  --start https://www.sat.gob.mx \
  --max-steps 20

# Ejecutar mision desde archivo
python -m webspider.cli run --mission missions/sat-login.json

# Retomar mision
python -m webspider.cli resume --checkpoint checkpoints/sat_20260807

# Listar checkpoints
python -m webspider.cli list-checkpoints

# Limpiar checkpoints antiguos
just clean-checkpoints
```

## Variables de entorno

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `LLM_BACKEND` | `openai` | `openai`, `hf`, `litellm` |
| `LLM_MODEL` | `gpt-4o` | Model ID |
| `LLM_API_KEY` | `""` | API key del proveedor |
| `LLM_API_BASE` | `""` | API base URL (OpenAI-compatible/Ollama) |
| `LLM_NUM_CTX` | `8192` | Context window size |
| `ETHER_WEBSEARCH_REPO` | `../ether-websearch` | Ruta al repo de ether-websearch |
| `MCP_REST_BASE_URL` | `http://127.0.0.1:8766` | URL del REST core de ether-websearch |

## Just tasks

```bash
just                # Lista todas las tasks
just up             # Levanta REST + MCP de ether-websearch
just down           # Detiene servicios
just test           # pytest con cobertura
just lint           # ruff check + format check
just typecheck      # mypy
just clean-checkpoints  # Elimina checkpoints antiguos
just demo           # Ejecuta una mision de demo contra books.toscrape
```
