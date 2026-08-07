# ROADMAP.md

## Ahora

### Iniciativas activas

- **`webspider-agent`** — Agente spider con CodeAgent + MCP +
  checkpoints + resume + solicitud de capacidades.

## Despues

### Siguientes prioridades (en orden)

1. **Parallel multi-seed** — Rastrear desde multiples URLs semilla
   en paralelo, consolidando hallazgos.
2. **Sitemap discovery** — Si ether-websearch implementa sitemap
   fetching (solicitado via `request_capability`), integrarlo como
   fuente de URLs de alta prioridad.
3. **Web dashboard** — UI web ligera para monitorear misiones activas,
   ver checkpoints y reportes (FastAPI + htmx).
4. **MCP server propio** — Exponer ether-webspider como MCP server
   para que otros agentes deleguen misiones de discovery.

### Apuestas futuras

- **Aprendizaje por refuerzo** — El agente aprende que patrones de
  URL/estructura de sitio correlacionan con encontrar el objetivo
  mas rapido.
- **Integracion con Burp Suite / ZAP** — Exportar hallazgos en
  formato compatible con herramientas de pentesting.

## No hacer por ahora

- **UI compleja** — El CLI es suficiente para el MVP.
- **Multi-agente** — Un solo agente es suficiente; CrewAI/Autogen
  seria overkill.
- **Despliegue cloud** — Es una herramienta local/desarrollo.
