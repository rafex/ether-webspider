# ether-webspider

Agente spider web orientado a objetivo con checkpoints y resume.
Usa `ether-websearch` como toolkit de herramientas via MCP.

**Fase:** Alpha — en desarrollo activo (v0.1.0)

## Que es

Un agente LLM (smolagents `CodeAgent`) que recibe un objetivo y
descubre endpoints —incluyendo tráfico browser, formularios, REST,
SOAP, GraphQL y gRPC— hasta encontrar lo encomendado. Conserva
requests y evidencia, no solo URLs, y genera checkpoints para poder
retomar sin persistir secretos.

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
  --max-steps 30 \
  --max-requests 200

# Probes seguros (HEAD/OPTIONS/GET) dentro de una allowlist
python -m webspider.cli run \
  --goal "Mapear requests de la aplicación" \
  --start https://example.com \
  --mode probe --allowed-domains example.com

# Cobertura activa: requiere confirmación explícita y allowlist
python -m webspider.cli run \
  --goal "Auditar el flujo autorizado de pedidos" \
  --start https://example.com \
  --mode active --confirm-active --allowed-domains example.com

# Retomar mision interrumpida
python -m webspider.cli resume --checkpoint checkpoints/abc123

# Levantar Web UI + WebSocket de control compartido
python -m webspider.cli serve

# Abrir el REPL de la misma misión
python -m webspider.cli chat --mission <mission_id>
```

La misión puede ejecutarse en `autonomous`, `interactive` o `hybrid`. Para
mostrar un navegador persistente usa `--headed --browser chromium|chrome|firefox|webkit`;
Safari real en macOS usa `--browser safari` y Selenium/SafariDriver. El control
en vivo está disponible mediante `pause`, `resume`, `takeover` y `release` en la
Web UI, WebSocket o REPL.

Para exponer la UI fuera de localhost configura un token y orígenes permitidos:

```bash
export WEBSPIDER_UI_TOKEN='token-local-de-desarrollo'
export WEBSPIDER_UI_ORIGINS='http://127.0.0.1:8787'
python -m webspider.cli serve --host 0.0.0.0
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
│   ├── supervisor.py  ← backend común autónomo/interactivo
│   ├── server.py      ← Web UI, REST y WebSocket
│   ├── secrets.py     ← Keychain/almacén cifrado efímero
│   └── cli.py         ← CLI run / resume / serve / chat
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
