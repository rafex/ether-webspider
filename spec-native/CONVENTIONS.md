# CONVENTIONS.md

Reglas operativas y de implementacion.

## Codigo

### Estilo Python

- **`from __future__ import annotations`** al inicio de cada archivo.
- **Type hints** completos en funciones publicas.
- **Prefijo `_`** para funciones/constantes privadas.
- **Docstrings** obligatorios en modulos y funciones publicas.
- **Strings:** comillas dobles `"` para docstrings, comillas simples `'` internas.
- **Longitud de linea:** 120 caracteres.
- **Imports:** agrupados: stdlib → terceros → locales.

### Estructura de archivo

```python
"""Docstring del modulo."""
from __future__ import annotations

# ── Imports stdlib ──

# ── Imports terceros ──

# ── Imports locales ──

# ── Constantes ──

# ── API publica ──

# ── Implementacion privada ──

if __name__ == "__main__":
    _cli()
```

Separadores de seccion: `# ── Nombre ──` con 80 chars de ancho.

## Testing

- Framework: pytest con pytest-cov.
- Mocking: unittest.mock (stdlib).
- Nombre: `test_<modulo>_<comportamiento>()`.
- Sin requests reales en unitarios.
- Cobertura minima: >=80%.

## Commits

- **Formato:** Conventional Commits con emoji.
  ```
  ✨ feat:    nueva funcionalidad
  🐛 fix:     correccion de bug
  ♻️ refactor: cambio de codigo sin cambiar comportamiento
  📝 docs:    documentacion
  ✅ test:    tests
  🔧 chore:   tareas de mantenimiento
  ```

## Branching

- **Modelo:** GitFlow simplificado.
  ```
  main        ← releases estables
  develop     ← integracion continua
  feature/*   ← nuevas funcionalidades
  ```

## Documentacion

- Los `README.md` indexan y orientan.
- Los archivos en `spec-native/` son fuente de verdad.
- No duplicar hechos entre documentos sin razon.
- Las decisiones que afecten futuros modulos van en `spec-native/DECISIONS.md`.

## Agentes (IAs trabajando en el repo)

- Antes de editar, leer el `README.md` de la carpeta.
- Actualizar el documento fuente si cambia una verdad compartida.
- No cerrar una tarea sin estado final y evidencia de validacion.
