# ether-webspider

Agente spider web orientado a objetivo con checkpoints y resume.
Usa `ether-websearch` como toolkit de herramientas via MCP.

**Fase:** Alpha — en desarrollo activo (v0.1.0)

## Que es

Un agente LLM (smolagents `CodeAgent`) que recibe un objetivo y
rastrea las redes de un sitio — via fetch, crawl, spider, search —
hasta encontrar lo encomendado. Genera checkpoints para poder retomar
donde se quedo.

Si `ether-websearch` no proporciona una herramienta necesaria,
el agente la solicita automaticamente al backlog SpecNative de
`ether-websearch`.

## Quick start

```bash
# Instalar
uv venv && uv pip install -e .

# Ejecutar REST + MCP de ether-websearch (requiere ether-websearch instalado)
just up

# Ejecutar mision
python -m webspider.cli run \
  --goal "Encontrar el endpoint de login y la API REST del sitio" \
  --start https://example.com \
  --max-steps 30

# Retomar mision interrumpida
python -m webspider.cli resume --checkpoint checkpoints/abc123
```

## Estructura

```
ether-webspider/
├── webspider/        ← paquete Python del agente
│   ├── agent.py      ← CodeAgent + tools
│   ├── checkpoint.py ← engine de checkpoints/resume
│   ├── config.py     ← factory LLM multi-proveedor
│   ├── mcp_client.py ← conector MCP → ether-websearch
│   ├── capabilities.py ← inventory + request_capability
│   ├── mission.py    ← parser de mision + reporte
│   └── cli.py        ← CLI run / resume
├── tests/            ← unit tests
├── checkpoints/      ← estado persistido de misiones
├── spec-native/      ← contexto SpecNative
└── TODO.md           ← tablero de tareas activo
```

## Documentacion

| Documento | Contenido |
|-----------|-----------|
| `spec-native/PRODUCT.md` | Problema, usuarios, objetivos |
| `spec-native/ARCHITECTURE.md` | Estructura del sistema |
| `spec-native/STACK.md` | Tecnologias y restricciones |
| `spec-native/specs/webspider-agent/SPEC.md` | Especificacion de la iniciativa |
| `spec-native/tasks/webspider-agent/TASKS.md` | Tareas ejecutables |

## Licencia

MIT
