# STACK.md

Fuente de verdad de la base tecnologica del proyecto.

## Runtime

- **Lenguaje:** Python
- **Version:** >=3.11 (mismo minimo que ether-websearch)
- **Plataforma:** Linux / macOS (Windows no es target)
- **Package manager:** uv

## Dependencias

### Core (obligatorias)

| Paquete | Version | Proposito |
|---------|---------|-----------|
| smolagents | >=1.10 | CodeAgent + MCPClient |
| mcp | >=1.2 | StdioServerParameters, tipos MCP |
| ether-websearch | >=0.1.0 | Toolkit de herramientas (path local) |

### LLM providers (al menos uno requerido)

| Paquete | Version | Backend |
|---------|---------|---------|
| huggingface_hub | >=0.20 | InferenceClientModel (HF) |
| openai | >=1.0 | OpenAIModel (OpenAI-compatible) |
| litellm | >=1.0 | LiteLLMModel (Ollama, Anthropic, etc.) |

## Build

- **Build system:** hatchling (consistente con ether-websearch)
- **Task runner:** Just — comandos de desarrollo, test, demo
- **No Make** — solo Just (proyecto ligero, sin build multi-stage)

## Testing

- **Framework:** pytest + pytest-cov
- **Mocking:** unittest.mock (stdlib)
- **Ubicacion:** tests/

## CI/CD

- **Platform:** GitHub Actions
- **Gates:** ruff, mypy, pytest
- **No publicacion PyPI** — el agente es para uso local/desarrollo

## Infraestructura

### ether-websearch (dependencia externa)

- **REST core:** debe estar corriendo para que el MCP funcione
  (DEC-0015/0016 de ether-websearch).
- **Orquestacion:** `just up` levanta REST (uvicorn) + MCP (stdio).
- **Ruta:** configurable via `ETHER_WEBSEARCH_REPO` (default:
  `../ether-websearch`).

### Checkpoints

- **Ubicacion:** `checkpoints/<mission_id>/`
- **Formato:** JSON (state.json + memory.jsonl)
- **Tamanio maximo:** ~10KB por step (memoria + state)
- **Retencion:** `just clean-checkpoints` elimina misiones finalizadas
  con >7 dias

## Restricciones

- Python >=3.11 (smolagents + ether-websearch lo requieren)
- No dependencias circulares con ether-websearch
- El agente nunca importa `websearch.src.*` directamente — solo via MCP
- Las tools locales (checkpoint, capabilities) deben ser stateless:
  toda la persistencia va a `checkpoints/`
