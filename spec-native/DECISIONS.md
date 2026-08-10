# DECISIONS.md

Registro de decisiones persistentes del proyecto.

## Formato

### DEC-XXXX — Titulo de la decision

- **Fecha:** YYYY-MM-DD
- **Estado:** proposed | accepted | deprecated | replaced
- **Contexto:** que problema obligo la decision
- **Decision:** que se decidio exactamente
- **Consecuencias:** costos, beneficios y limites
- **Reemplaza:** DEC-XXXX o none

---

### DEC-0001 — CodeAgent de smolagents como framework del agente

- **Fecha:** 2026-08-07
- **Estado:** accepted
- **Contexto:** Se necesitaba un framework de agente LLM que permitiera
  tool use generativo (el agente escribe y ejecuta codigo Python que
  llama a las tools), integracion con MCP, y persistencia de memoria.
  Las alternativas evaluadas: loop propio ligero (maximo control pero
  reinventa tool-use parsing), LangChain (pesado, abstracciones
  innecesarias), CrewAI (multi-agente, overkill para un solo agente).
- **Decision:** Usar `smolagents.CodeAgent` con `MCPClient` para
  cargar las tools de ether-websearch. El agente genera y ejecuta
  codigo Python — esto es superior a un loop de prompts porque el
  agente puede escribir logica condicional, loops, y manejo de
  errores directamente en el codigo generado.
- **Consecuencias:**
  - Ventajas: integracion MCP nativa via stdio subprocess, memoria
    serializable (`agent.memory.steps`), multi-proveedor LLM.
  - Limitaciones: requiere Python >=3.11, el agente necesita un
    modelo con buena capacidad de generacion de codigo.
- **Reemplaza:** none

### DEC-0005 — Descubrimiento de endpoints centrado en requests

- **Fecha:** 2026-08-09
- **Estado:** accepted
- **Contexto:** El crawling de URLs no conserva suficiente evidencia para reconstruir APIs reales: faltaban tráfico XHR/fetch, métodos, payloads, respuestas, artefactos de contrato y protocolos no REST.
- **Decision:** `ether-websearch` ejecuta observación y probing; `ether-webspider` orquesta la misión y persiste findings estructurados. La exploración activa es opt-in, requiere allowlist y confirmación, y toda persistencia redacciona credenciales, cookies, tokens y storage state.
- **Consecuencias:** Se pueden mapear requests dinámicos, formularios, OpenAPI/WSDL/GraphQL/proto y gRPC/gRPC-Web sin convertir WebSpider en un scraper de contenido. Replay y reflexión quedan acotados por política explícita.
- **Reemplaza:** none

### DEC-0006 — Supervisor único para autonomía y takeover humano

- **Fecha:** 2026-08-09
- **Estado:** accepted
- **Contexto:** El usuario debe poder observar un navegador visible, intervenir
  durante un flujo autenticado y devolver el control al agente sin duplicar
  la lógica de misión.
- **Decision:** `MissionSupervisor` es el backend común de `run`, Web UI,
  WebSocket y REPL. Ejecuta unidades de un step, conserva la sesión de
  navegador por `session_id`, y aplica pause/resume/takeover/release. El modo
  autónomo es el default; el modo activo y las mutaciones requieren allowlist,
  confirmación y límites explícitos.
- **Consecuencias:** La intervención humana y la ejecución desatendida
  comparten estado, findings, requests y checkpoints. Safari real queda
  condicionado a SafariDriver/macOS; Playwright WebKit es la alternativa
  multiplataforma.
- **Reemplaza:** none

### DEC-0002 — Checkpoints hibridos: state tools JSON + memoria serializada

- **Fecha:** 2026-08-07
- **Estado:** accepted
- **Contexto:** El agente CodeAgent ejecuta codigo en un sandbox.
  Las variables del codigo generado (frontier, visited, findings) se
  pierden si el proceso termina. smolagents permite serializar la
  memoria (`agent.memory.steps`) pero eso solo captura el contexto
  de razonamiento, no los datos operacionales.
- **Decision:** Dos mecanismos complementarios: (1) state tools
  `save_checkpoint`/`load_checkpoint` que persisten frontier, visited
  y findings en JSON — el agente las llama explicitamente en el codigo
  generado; (2) step callback que serializa `agent.memory.steps` a
  `memory.jsonl` tras cada step. En resume, se cargan ambos.
- **Consecuencias:**
  - Ventajas: frontier/findings sobreviven incluso si el LLM genera
    codigo que no los persiste; la memoria da continuidad de
    razonamiento. El formato JSON es portable y diffable.
  - Limitaciones: el agente debe ser instruido para usar
    `save_checkpoint` en su codigo generado (prompt engineering).
- **Reemplaza:** none

### DEC-0003 — Feature requests al backlog SpecNative de ether-websearch

- **Fecha:** 2026-08-07
- **Estado:** accepted
- **Contexto:** Durante una mision, el agente puede detectar que
  ether-websearch carece de una capacidad necesaria (ej: "fetch
  sitemap.xml", "parsear JSON-LD", "descubrir paginacion"). Se
  necesita un canal formal para solicitar la construccion de esa
  tool, sin que el agente tenga que implementarla.
- **Decision:** Tool `request_capability(name, description, use_case)`
  que escribe un feature request estructurado (JSON dentro de un
  bloque markdown) en `<ETHER_WEBSEARCH_REPO>/spec-native/intake/IDEAS.md`.
  Esto cierra el loop: el agente solicita, el equipo de ether-websearch
  prioriza e implementa. Usa el intake SpecNative de ether-websearch
  como unico punto de entrada de solicitudes.
- **Consecuencias:**
  - Ventajas: canal unico, trazable, sin dependencia de APIs externas
    (GitHub issues). El formato JSON es parseable.
  - Limitaciones: requiere acceso de escritura al repo de
    ether-websearch (filesystem local). No notifica automaticamente
    al equipo (se resuelve con git diff o CI).
- **Reemplaza:** none

### DEC-0004 — LLM multi-proveedor via variables de entorno

- **Fecha:** 2026-08-07
- **Estado:** accepted
- **Contexto:** El agente debe funcionar con distintos backends LLM
  segun el entorno del usuario: HF (gratuito, requiere token),
  OpenAI-compatible (incluye Ollama local, OpenRouter, Groq),
  LiteLLM (maxima compatibilidad). No se quiere forzar una dependencia
  pesada.
- **Decision:** Factory `get_model()` en `webspider.config` que lee
  `LLM_BACKEND` (default: `openai`), `LLM_MODEL`, `LLM_API_KEY`,
  `LLM_API_BASE`, `LLM_NUM_CTX`. Soporta tres backends:
  - `openai` → `OpenAIModel(model_id, api_base, api_key)`
  - `hf` → `InferenceClientModel(model_id, token)`
  - `litellm` → `LiteLLMModel(model_id, api_base, api_key, num_ctx)`
  Las dependencias de cada backend son opcionales (import lazy con
  `ImportError` amigable).
- **Consecuencias:**
  - Ventajas: el mismo agente funciona con Ollama local (gratis),
    OpenAI (calidad), HF (balance). Configuracion simple via .env.
  - Limitaciones: los modelos locales pequenos (Ollama 7B) pueden no
    generar codigo Python correcto — documentar modelos recomendados.
- **Reemplaza:** none

### DEC-0007 — Auditoría de ether-rules gobernada desde WebSpider

- **Fecha:** 2026-08-09
- **Estado:** accepted
- **Contexto:** `ether-my-best-practice` es el estándar consumido por WebSpider,
  pero actualmente no contiene una estructura SpecNative propia. La auditoría
  necesita quedar versionada, trazable y disponible para los agentes que usan
  el estándar.
- **Decision:** Mantener la SPEC y las tareas de cumplimiento de ether-rules en
  `ether-webspider/spec-native/`, con un vínculo cross-repo explícito al
  repositorio mantenedor. Las correcciones se ejecutarán por fases y se
  distinguirán las reglas del mantenedor de las reglas para consumidores.
- **Consecuencias:** WebSpider conserva la fuente de contexto y continuidad;
  ether-rules sigue siendo la fuente de verdad del contenido de las reglas.
  Las tareas que modifiquen ether-rules deberán registrar evidencia en su
  propio repositorio y reflejar el resultado aquí.
- **Reemplaza:** none
