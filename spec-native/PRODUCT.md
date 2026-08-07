# PRODUCT.md

Fuente de verdad del producto.

## Problema

Los agentes de IA necesitan rastrear sitios web de forma inteligente
— no solo BFS ciego, sino orientado a un objetivo concreto ("encontrar
el login", "descubrir la API REST de pricing"). Las herramientas
actuales de crawling no incorporan decision LLM para priorizar que
URLs explorar, no persisten estado para retomar desde un checkpoint,
y no detectan gaps de capacidad en el toolkit subyacente.

**ether-webspider** resuelve esto con un agente CodeAgent (smolagents)
que consume `ether-websearch` via MCP, rastrea con orientacion al
objetivo, genera checkpoints, y solicita herramientas faltantes.

## Usuarios

- **Pentesters y security researchers:** necesitan mapear la superficie
  de ataque de un sitio — descubrir logins, APIs, endpoints SOAP/REST,
  formularios, paginas de autenticacion.
- **Desarrolladores y arquitectos:** necesitan documentar los endpoints
  de un sistema legacy sin acceso al codigo fuente, explorando desde
  la URL publica.
- **Agentes de IA compuestos:** que delegan el discovery de endpoints
  a ether-webspider como sub-agente especializado.

## Objetivos

- **Rastreo orientado a objetivo:** el LLM puntua y prioriza URLs
  candidatas por relevancia al objetivo, no BFS ciego.
- **Checkpoints/resume:** estado persistido en disco (JSON) que
  permite reanudar una mision desde donde se interrumpio.
- **Integracion MCP con ether-websearch:** consume las 15+ tools
  del MCP server existente (spider, crawl, fetch, search, navigate,
  browser, social, download).
- **Deteccion de gaps:** el agente identifica cuando le falta una
  capacidad y emite un feature request al backlog SpecNative de
  ether-websearch.

### Metricas de exito

- El agente encuentra el endpoint objetivo en <30 pasos para un sitio
  tipico (ej: books.toscrape o un portal gubernamental).
- Un checkpoint se escribe tras cada tool call (perdida maxima de
  progreso: 1 paso).
- El resume desde checkpoint recupera exactamente el mismo estado
  (memoria del agente + frontier + findings).

## No objetivos

- **No es un crawler BFS.** La logica de crawling la provee
  `ether-websearch.spider`; el agente solo decide que explorar.
- **No es un SaaS ni API server.** Se ejecuta localmente como CLI.
- **No construye herramientas nuevas** en ether-websearch. Si detecta
  un gap, emite una solicitud; no implementa la tool.

## Valor diferencial

1. **CodeAgent con tool use real:** smolagents genera y ejecuta codigo
   Python que llama a las tools MCP — no es solo un loop de prompts.
2. **Checkpoints atomicos:** la combinacion de state tools + memoria
   serializada permite retomar sin perder contexto.
3. **Multi-proveedor LLM:** el mismo agente funciona con HF, OpenAI,
   Ollama local — configurable por variables de entorno.
4. **Ciclo cerrado con ether-websearch:** si falta una capacidad, el
   agente la solicita formalmente al backlog del toolkit, cerrando
   el loop de mejora continua.
