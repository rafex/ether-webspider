# CI.md

Pipeline de integracion continua.

## Gates

| Gate | Comando | Criticidad |
|------|---------|------------|
| Lint | `ruff check webspider/ tests/` | Alta — bloquea merge |
| Format | `ruff format --check webspider/ tests/` | Alta — bloquea merge |
| Type check | `mypy webspider/` | Alta — bloquea merge |
| Unit tests | `pytest tests/ -v --cov=webspider` | Alta — bloquea merge |
| Coverage | `--cov-fail-under=80` | Media — warning |

## Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - uses: astral-sh/setup-uv@v4
      - run: uv venv && uv pip install -e ".[dev]"
      - run: ruff check webspider/ tests/
      - run: ruff format --check webspider/ tests/
      - run: mypy webspider/
      - run: pytest tests/ -v --cov=webspider --cov-report=term-missing
```

## Variables de entorno en CI

| Variable | Valor | Nota |
|----------|-------|------|
| `LLM_BACKEND` | `openai` | No se usa en tests unitarios (mock) |
| `ETHER_WEBSEARCH_REPO` | `/tmp/ether-websearch-test` | Path de prueba para bridge |

## CD

No hay pipeline de publicacion — ether-webspider es para uso local.
